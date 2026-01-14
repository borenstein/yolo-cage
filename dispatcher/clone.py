"""Clone operations for workspace bootstrap.

Handles cloning a repository into an empty workspace directory.
"""

import logging
from pathlib import Path

from .config import REPO_URL
from .git import execute_with_auth, execute

logger = logging.getLogger(__name__)


class CloneError(Exception):
    """Error during clone operation."""
    pass


def clone_and_checkout(workspace: Path, branch: str) -> dict:
    """
    Clone repository into empty workspace and checkout branch.

    Args:
        workspace: Empty directory to clone into
        branch: Branch to checkout (created if doesn't exist)

    Returns:
        Status dict with workspace, branch, action, cloned keys

    Raises:
        CloneError on failure
    """
    result = execute_with_auth(
        ["clone", REPO_URL, str(workspace)],
        cwd=str(workspace.parent)
    )

    if result.exit_code != 0:
        raise CloneError(f"Failed to clone repository: {result.stderr}")

    action = _checkout_branch(workspace, branch)

    return {
        "status": "success",
        "workspace": str(workspace),
        "branch": branch,
        "action": action,
        "cloned": True,
    }


def _checkout_branch(workspace: Path, branch: str) -> str:
    """
    Checkout branch, creating it if it doesn't exist on remote.

    Returns action string: "checked_out" or "created"
    """
    if _branch_exists_on_remote(workspace, branch):
        result = execute(["checkout", branch], cwd=str(workspace))
        if result.exit_code != 0:
            raise CloneError(f"Failed to checkout branch {branch}: {result.stderr}")
        return "checked_out"
    else:
        result = execute(["checkout", "-b", branch], cwd=str(workspace))
        if result.exit_code != 0:
            raise CloneError(f"Failed to create branch {branch}: {result.stderr}")
        return "created"


def _branch_exists_on_remote(workspace: Path, branch: str) -> bool:
    """Check if branch exists on origin."""
    result = execute(
        ["ls-remote", "--heads", "origin", branch],
        cwd=str(workspace)
    )
    return branch in result.stdout
