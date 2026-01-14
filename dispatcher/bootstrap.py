"""Workspace bootstrap entry point for yolo-cage pods.

This module orchestrates initial workspace setup. It detects the workspace
state and delegates to the appropriate module for handling.
"""

import logging
from pathlib import Path

from .config import WORKSPACE_ROOT, REPO_URL
from .clone import clone_and_checkout, CloneError
from .sync import update_workspace, initialize_with_existing_files, SyncError

logger = logging.getLogger(__name__)


class BootstrapError(Exception):
    """Error during workspace bootstrap."""
    pass


def bootstrap_workspace(branch: str) -> dict:
    """
    Bootstrap a workspace for the given branch.

    Called during pod init, before the agent starts. Detects workspace
    state and delegates to appropriate handler:
    - Empty directory: clone fresh
    - Has .git: update existing
    - Has files but no .git: initialize with existing files

    Args:
        branch: Branch name to checkout/create

    Returns:
        Dict with status, workspace, branch, action, cloned keys

    Raises:
        BootstrapError on failure
    """
    if not REPO_URL:
        raise BootstrapError(
            "REPO_URL not configured. Set it in dispatcher-config ConfigMap."
        )

    workspace = Path(WORKSPACE_ROOT) / branch
    workspace.mkdir(parents=True, exist_ok=True)

    try:
        state = _detect_workspace_state(workspace)
        logger.info(f"Workspace {workspace} state: {state}")

        if state == "has_git":
            return update_workspace(workspace, branch)
        elif state == "has_files":
            return initialize_with_existing_files(workspace, branch)
        else:
            return clone_and_checkout(workspace, branch)

    except (CloneError, SyncError) as e:
        raise BootstrapError(str(e)) from e


def _detect_workspace_state(workspace: Path) -> str:
    """
    Detect workspace state.

    Returns:
        "has_git" - existing git repository
        "has_files" - files present but no .git
        "empty" - no files
    """
    git_dir = workspace / ".git"
    if git_dir.exists():
        return "has_git"

    if any(workspace.iterdir()):
        return "has_files"

    return "empty"
