"""Path translation between agent and dispatcher filesystems."""

from .config import WORKSPACE_ROOT

# Agent's workspace path (matches pod mount point)
AGENT_WORKSPACE = "/home/dev/workspace"


def translate_cwd(agent_cwd: str, branch: str) -> str:
    """
    Translate agent's cwd to dispatcher's filesystem path.

    Agent sees /home/dev/workspace, dispatcher has /workspaces/{branch}.
    """
    if agent_cwd == AGENT_WORKSPACE:
        return f"{WORKSPACE_ROOT}/{branch}"
    if agent_cwd.startswith(AGENT_WORKSPACE + "/"):
        relative = agent_cwd[len(AGENT_WORKSPACE) + 1:]
        return f"{WORKSPACE_ROOT}/{branch}/{relative}"
    # Fallback: use as-is (shouldn't happen in normal operation)
    return agent_cwd
