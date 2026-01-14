"""Workspace bootstrap for yolo-cage pods.

This module handles initial workspace setup - cloning the repository
and checking out the correct branch. This runs with dispatcher privileges
(has PAT, can clone) before the agent starts.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from .config import WORKSPACE_ROOT, REPO_URL, GITHUB_PAT, GIT_USER_NAME, GIT_USER_EMAIL
from .git import execute_with_auth, execute

logger = logging.getLogger(__name__)


class BootstrapError(Exception):
    """Error during workspace bootstrap."""
    pass


def bootstrap_workspace(branch: str) -> dict:
    """
    Bootstrap a workspace for the given branch.

    This is called during pod init, before the agent starts. It:
    1. Creates the workspace directory if needed
    2. Clones the repo if the workspace is empty
    3. Checks out the requested branch (creating it if needed)

    Returns dict with status info.
    Raises BootstrapError on failure.
    """
    if not REPO_URL:
        raise BootstrapError(
            "REPO_URL not configured. Set it in dispatcher-config ConfigMap."
        )

    workspace = Path(WORKSPACE_ROOT) / branch

    # Create workspace directory
    workspace.mkdir(parents=True, exist_ok=True)

    # Check if already a git repo
    git_dir = workspace / ".git"
    if git_dir.exists():
        logger.info(f"Workspace {workspace} already initialized, updating")
        return _update_existing_workspace(workspace, branch)

    # Check if workspace has files (but not .git)
    if any(workspace.iterdir()):
        # Workspace has files but no .git - could be leftover data
        # We'll initialize git here
        logger.info(f"Workspace {workspace} has files but no .git, initializing")
        return _initialize_workspace_with_existing_files(workspace, branch)

    # Fresh workspace - clone into it
    logger.info(f"Cloning {REPO_URL} into {workspace}")
    return _clone_fresh_workspace(workspace, branch)


def _clone_fresh_workspace(workspace: Path, branch: str) -> dict:
    """Clone repo into empty workspace and set up branch."""

    # Clone the repo
    result = execute_with_auth(
        ["clone", REPO_URL, str(workspace)],
        cwd=str(workspace.parent)
    )

    if result.exit_code != 0:
        raise BootstrapError(f"Failed to clone repository: {result.stderr}")

    # Check if the branch exists on remote
    result = execute(
        ["ls-remote", "--heads", "origin", branch],
        cwd=str(workspace)
    )

    branch_exists = branch in result.stdout

    if branch_exists:
        # Checkout existing branch
        result = execute(["checkout", branch], cwd=str(workspace))
        if result.exit_code != 0:
            raise BootstrapError(f"Failed to checkout branch {branch}: {result.stderr}")
        action = "checked_out"
    else:
        # Create new branch from default branch
        result = execute(["checkout", "-b", branch], cwd=str(workspace))
        if result.exit_code != 0:
            raise BootstrapError(f"Failed to create branch {branch}: {result.stderr}")
        action = "created"

    return {
        "status": "success",
        "workspace": str(workspace),
        "branch": branch,
        "action": action,
        "cloned": True,
    }


def _update_existing_workspace(workspace: Path, branch: str) -> dict:
    """Update an existing workspace - fetch and ensure on correct branch."""

    # Fetch latest
    result = execute_with_auth(["fetch", "origin"], cwd=str(workspace))
    if result.exit_code != 0:
        logger.warning(f"Failed to fetch: {result.stderr}")

    # Get current branch
    result = execute(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(workspace))
    current_branch = result.stdout.strip() if result.exit_code == 0 else None

    if current_branch == branch:
        return {
            "status": "success",
            "workspace": str(workspace),
            "branch": branch,
            "action": "already_on_branch",
            "cloned": False,
        }

    # Need to switch branches
    # Check if branch exists locally
    result = execute(["show-ref", "--verify", f"refs/heads/{branch}"], cwd=str(workspace))
    branch_exists_locally = result.exit_code == 0

    if branch_exists_locally:
        result = execute(["checkout", branch], cwd=str(workspace))
    else:
        # Check if it exists on remote
        result = execute(["ls-remote", "--heads", "origin", branch], cwd=str(workspace))
        if branch in result.stdout:
            result = execute(["checkout", "-b", branch, f"origin/{branch}"], cwd=str(workspace))
        else:
            result = execute(["checkout", "-b", branch], cwd=str(workspace))

    if result.exit_code != 0:
        raise BootstrapError(f"Failed to checkout branch {branch}: {result.stderr}")

    return {
        "status": "success",
        "workspace": str(workspace),
        "branch": branch,
        "action": "switched_branch",
        "cloned": False,
    }


def _initialize_workspace_with_existing_files(workspace: Path, branch: str) -> dict:
    """Handle workspace with files but no .git (e.g., leftover CLAUDE.md)."""

    # Initialize git
    result = execute(["init"], cwd=str(workspace))
    if result.exit_code != 0:
        raise BootstrapError(f"Failed to init git: {result.stderr}")

    # Add remote
    result = execute(["remote", "add", "origin", REPO_URL], cwd=str(workspace))
    if result.exit_code != 0:
        raise BootstrapError(f"Failed to add remote: {result.stderr}")

    # Fetch
    result = execute_with_auth(["fetch", "origin"], cwd=str(workspace))
    if result.exit_code != 0:
        raise BootstrapError(f"Failed to fetch: {result.stderr}")

    # Check if branch exists on remote
    result = execute(["ls-remote", "--heads", "origin", branch], cwd=str(workspace))
    branch_exists = branch in result.stdout

    if branch_exists:
        # Reset to remote branch (keeps local files as modifications)
        result = execute(["reset", f"origin/{branch}"], cwd=str(workspace))
        if result.exit_code != 0:
            raise BootstrapError(f"Failed to reset to origin/{branch}: {result.stderr}")

        # Checkout to get proper tracking
        result = execute(["checkout", "-B", branch, f"origin/{branch}"], cwd=str(workspace))
        action = "initialized_from_remote"
    else:
        # Get default branch and branch from there
        result = execute(["remote", "show", "origin"], cwd=str(workspace))
        # Parse default branch from output - look for "HEAD branch:"
        default_branch = "main"  # fallback
        for line in result.stdout.split('\n'):
            if "HEAD branch:" in line:
                default_branch = line.split(":")[-1].strip()
                break

        result = execute(["checkout", "-b", branch, f"origin/{default_branch}"], cwd=str(workspace))
        action = "initialized_new_branch"

    if result.exit_code != 0:
        raise BootstrapError(f"Failed to setup branch {branch}: {result.stderr}")

    return {
        "status": "success",
        "workspace": str(workspace),
        "branch": branch,
        "action": action,
        "cloned": False,
    }
