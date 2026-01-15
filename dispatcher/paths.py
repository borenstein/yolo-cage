"""Path translation between agent and dispatcher filesystems."""

from .config import WORKSPACE_ROOT


def translate_cwd(agent_cwd: str, branch: str) -> str:
    """
    Translate agent's cwd to dispatcher's filesystem path.

    Agent sees /workspace, dispatcher has /workspaces/{branch}.
    """
    if agent_cwd == "/workspace":
        return f"{WORKSPACE_ROOT}/{branch}"
    if agent_cwd.startswith("/workspace/"):
        return f"{WORKSPACE_ROOT}/{branch}/{agent_cwd[11:]}"
    # Fallback: use as-is (shouldn't happen in normal operation)
    return agent_cwd
