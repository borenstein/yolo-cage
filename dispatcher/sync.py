"""Workspace sync operations for bootstrap.

Handles updating existing workspaces and initializing workspaces
that have files but no git repository.
"""

import logging
from pathlib import Path

from .config import REPO_URL
from .git import execute_with_auth, execute

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Error during sync operation."""
    pass


def update_workspace(workspace: Path, branch: str) -> dict:
    """
    Update existing git workspace - fetch and ensure on correct branch.

    Args:
        workspace: Directory with existing .git
        branch: Branch to be on

    Returns:
        Status dict with workspace, branch, action, cloned keys

    Raises:
        SyncError on failure
    """
    _fetch_origin(workspace)

    current = _get_current_branch(workspace)
    if current == branch:
        return {
            "status": "success",
            "workspace": str(workspace),
            "branch": branch,
            "action": "already_on_branch",
            "cloned": False,
        }

    _switch_to_branch(workspace, branch)

    return {
        "status": "success",
        "workspace": str(workspace),
        "branch": branch,
        "action": "switched_branch",
        "cloned": False,
    }


def initialize_with_existing_files(workspace: Path, branch: str) -> dict:
    """
    Initialize git in workspace that has files but no .git directory.

    This handles cases like leftover files from a previous workspace.

    Args:
        workspace: Directory with files but no .git
        branch: Branch to setup

    Returns:
        Status dict with workspace, branch, action, cloned keys

    Raises:
        SyncError on failure
    """
    _init_and_add_remote(workspace)
    _fetch_origin(workspace, raise_on_error=True)
    action = _setup_branch_with_existing_files(workspace, branch)

    return {
        "status": "success",
        "workspace": str(workspace),
        "branch": branch,
        "action": action,
        "cloned": False,
    }


def _fetch_origin(workspace: Path, raise_on_error: bool = False) -> None:
    """Fetch from origin. Optionally raise on failure."""
    result = execute_with_auth(["fetch", "origin"], cwd=str(workspace))
    if result.exit_code != 0:
        if raise_on_error:
            raise SyncError(f"Failed to fetch: {result.stderr}")
        logger.warning(f"Failed to fetch: {result.stderr}")


def _get_current_branch(workspace: Path) -> str | None:
    """Get name of current branch, or None if detached/error."""
    result = execute(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(workspace))
    return result.stdout.strip() if result.exit_code == 0 else None


def _switch_to_branch(workspace: Path, branch: str) -> None:
    """Switch to branch, checking local then remote."""
    if _branch_exists_locally(workspace, branch):
        result = execute(["checkout", branch], cwd=str(workspace))
    elif _branch_exists_on_remote(workspace, branch):
        result = execute(
            ["checkout", "-b", branch, f"origin/{branch}"],
            cwd=str(workspace)
        )
    else:
        result = execute(["checkout", "-b", branch], cwd=str(workspace))

    if result.exit_code != 0:
        raise SyncError(f"Failed to checkout branch {branch}: {result.stderr}")


def _branch_exists_locally(workspace: Path, branch: str) -> bool:
    """Check if branch exists as local ref."""
    result = execute(
        ["show-ref", "--verify", f"refs/heads/{branch}"],
        cwd=str(workspace)
    )
    return result.exit_code == 0


def _branch_exists_on_remote(workspace: Path, branch: str) -> bool:
    """Check if branch exists on origin."""
    result = execute(
        ["ls-remote", "--heads", "origin", branch],
        cwd=str(workspace)
    )
    return branch in result.stdout


def _init_and_add_remote(workspace: Path) -> None:
    """Initialize git and add origin remote."""
    result = execute(["init"], cwd=str(workspace))
    if result.exit_code != 0:
        raise SyncError(f"Failed to init git: {result.stderr}")

    result = execute(["remote", "add", "origin", REPO_URL], cwd=str(workspace))
    if result.exit_code != 0:
        raise SyncError(f"Failed to add remote: {result.stderr}")


def _setup_branch_with_existing_files(workspace: Path, branch: str) -> str:
    """Setup branch in newly initialized repo with existing files."""
    if _branch_exists_on_remote(workspace, branch):
        result = execute(["reset", f"origin/{branch}"], cwd=str(workspace))
        if result.exit_code != 0:
            raise SyncError(f"Failed to reset to origin/{branch}: {result.stderr}")

        result = execute(
            ["checkout", "-B", branch, f"origin/{branch}"],
            cwd=str(workspace)
        )
        action = "initialized_from_remote"
    else:
        default_branch = _get_default_branch(workspace)
        result = execute(
            ["checkout", "-b", branch, f"origin/{default_branch}"],
            cwd=str(workspace)
        )
        action = "initialized_new_branch"

    if result.exit_code != 0:
        raise SyncError(f"Failed to setup branch {branch}: {result.stderr}")

    return action


def _get_default_branch(workspace: Path) -> str:
    """Get default branch from remote, fallback to 'main'."""
    result = execute(["remote", "show", "origin"], cwd=str(workspace))
    for line in result.stdout.split('\n'):
        if "HEAD branch:" in line:
            return line.split(":")[-1].strip()
    return "main"
