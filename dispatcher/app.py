"""FastAPI application and request handlers."""

import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

from . import registry
from .bootstrap import bootstrap_workspace, BootstrapError
from .commands import CommandCategory, classify, get_subcommand
from .config import WORKSPACE_ROOT
from .gh import execute as gh_execute
from .gh_commands import GhCommandCategory, classify_gh
from .git import execute, execute_with_auth
from .hooks import run_pre_push_hooks
from .models import GitRequest, GhRequest
from .policy import check_branch_switch, check_merge_allowed, check_push_allowed


def _translate_cwd(agent_cwd: str, branch: str) -> str:
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="yolo-cage Git Dispatcher", version="0.2.0")


def _denial_response(message: str) -> PlainTextResponse:
    """Create a denial response."""
    return PlainTextResponse(
        content=message,
        headers={"X-Yolo-Cage-Exit-Code": "1"},
    )


def _git_response(output: str, exit_code: int) -> PlainTextResponse:
    """Create a git output response."""
    return PlainTextResponse(
        content=output,
        headers={"X-Yolo-Cage-Exit-Code": str(exit_code)},
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/register")
async def register_pod(request: Request, branch: str):
    """Register a pod IP -> branch mapping."""
    client_ip = request.client.host
    registry.register(client_ip, branch)
    return {"status": "registered", "ip": client_ip, "branch": branch}


@app.delete("/register")
async def deregister_pod(request: Request):
    """Remove a pod from the registry."""
    client_ip = request.client.host
    branch = registry.deregister(client_ip)
    if branch:
        return {"status": "deregistered", "ip": client_ip}
    return {"status": "not_found", "ip": client_ip}


@app.get("/registry")
async def list_registry():
    """List all registered pods."""
    return {"registry": registry.list_all()}


@app.post("/bootstrap")
async def bootstrap(branch: str):
    """
    Bootstrap a workspace for a branch.

    This is called during pod init to set up the workspace before the agent
    starts. It clones the repository and checks out the requested branch.

    This endpoint runs with dispatcher privileges (has PAT, can clone).
    The agent never needs clone/init access.
    """
    logger.info(f"Bootstrap requested for branch: {branch}")
    try:
        result = bootstrap_workspace(branch)
        logger.info(f"Bootstrap complete: {result}")
        return result
    except BootstrapError as e:
        logger.error(f"Bootstrap failed: {e}")
        raise HTTPException(500, str(e))


@app.post("/git", response_class=PlainTextResponse)
async def handle_git(git_req: GitRequest, request: Request):
    """Handle a git command from a sandbox pod."""
    client_ip = request.client.host
    assigned_branch = registry.get_branch(client_ip)

    if assigned_branch is None:
        logger.warning(f"Unregistered pod {client_ip} attempted git operation")
        raise HTTPException(403, "yolo-cage: pod not registered. Contact cluster admin.")

    # Translate agent's /workspace to dispatcher's /workspaces/{branch}
    cwd = _translate_cwd(git_req.cwd, assigned_branch)

    logger.info(f"Git from {client_ip} ({assigned_branch}): {git_req.args}")

    category, deny_message = classify(git_req.args)

    if category == CommandCategory.DENIED:
        return _denial_response(deny_message + "\n")

    if category == CommandCategory.UNKNOWN:
        return _denial_response("yolo-cage: unrecognized or disallowed git operation\n")

    # Branch switch: execute but warn if switching away
    if category == CommandCategory.BRANCH:
        warning = check_branch_switch(git_req.args, assigned_branch)
        result = execute(git_req.args, cwd)
        output = (warning + "\n" if warning else "") + result.stdout + result.stderr
        return _git_response(output, result.exit_code)

    # Merge: must be on assigned branch
    if category == CommandCategory.MERGE:
        error = check_merge_allowed(cwd, assigned_branch, get_subcommand(git_req.args))
        if error:
            return _denial_response(error)
        result = execute(git_req.args, cwd)
        return _git_response(result.stdout + result.stderr, result.exit_code)

    # Push: branch enforcement + pre-push hooks
    if category == CommandCategory.REMOTE_WRITE:
        error = check_push_allowed(git_req.args, cwd, assigned_branch)
        if error:
            return _denial_response(error)

        hook_ok, hook_output = run_pre_push_hooks(cwd)
        if not hook_ok:
            return _denial_response(f"yolo-cage: push rejected by pre-push hooks\n\n{hook_output}")

        result = execute_with_auth(git_req.args, cwd)
        return _git_response(result.stdout + result.stderr, result.exit_code)

    # Remote read (fetch/pull): just needs auth
    if category == CommandCategory.REMOTE_READ:
        result = execute_with_auth(git_req.args, cwd)
        return _git_response(result.stdout + result.stderr, result.exit_code)

    # Local operations: no restrictions
    result = execute(git_req.args, cwd)
    return _git_response(result.stdout + result.stderr, result.exit_code)


@app.post("/gh", response_class=PlainTextResponse)
async def handle_gh(gh_req: GhRequest, request: Request):
    """Handle a gh CLI command from a sandbox pod."""
    client_ip = request.client.host
    assigned_branch = registry.get_branch(client_ip)

    if assigned_branch is None:
        logger.warning(f"Unregistered pod {client_ip} attempted gh operation")
        raise HTTPException(403, "yolo-cage: pod not registered. Contact cluster admin.")

    # Translate agent's /workspace to dispatcher's /workspaces/{branch}
    cwd = _translate_cwd(gh_req.cwd, assigned_branch)

    logger.info(f"gh from {client_ip} ({assigned_branch}): {gh_req.args}")

    category, deny_message = classify_gh(gh_req.args)

    if category == GhCommandCategory.BLOCKED:
        return _denial_response(deny_message + "\n")

    if category == GhCommandCategory.UNKNOWN:
        return _denial_response("yolo-cage: unrecognized or disallowed gh operation\n")

    # Allowed: execute with authentication
    result = gh_execute(gh_req.args, cwd)
    return _git_response(result.stdout + result.stderr, result.exit_code)
