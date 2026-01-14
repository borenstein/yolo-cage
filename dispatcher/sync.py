"""Workspace sync operations for bootstrap.

Handles updating existing workspaces (those with a .git directory).
"""

import logging
from pathlib import Path

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


def _fetch_origin(workspace: Path) -> None:
    """Fetch from origin, logging warning on failure."""
    result = execute_with_auth(["fetch", "origin"], cwd=str(workspace))
    if result.exit_code != 0:
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
