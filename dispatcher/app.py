"""FastAPI application and route definitions."""

import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

from . import registry
from . import pods
from .handlers import git as git_handler
from .handlers import gh as gh_handler
from .bootstrap import bootstrap_workspace, BootstrapError
from .models import GitRequest, GhRequest, PodCreateRequest, PodInfo, PodListResponse, PodCreateResponse
from .paths import translate_cwd


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="yolo-cage Git Dispatcher", version="0.2.0")


def handle_pod_operation(operation_name: str, func, *args, **kwargs):
    """Execute a pod operation with consistent error handling.

    Re-raises HTTPException as-is, converts other exceptions to 500.
    """
    try:
        return func(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{operation_name}: {e}")
        raise HTTPException(500, str(e))


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

    Called during pod init to clone the repository and check out the branch.
    Runs with dispatcher privileges (has PAT, can clone).
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

    cwd = translate_cwd(git_req.cwd, assigned_branch)
    logger.info(f"Git from {client_ip} ({assigned_branch}): {git_req.args}")

    return git_handler.handle(git_req.args, cwd, assigned_branch)


@app.post("/gh", response_class=PlainTextResponse)
async def handle_gh(gh_req: GhRequest, request: Request):
    """Handle a gh CLI command from a sandbox pod."""
    client_ip = request.client.host
    assigned_branch = registry.get_branch(client_ip)

    if assigned_branch is None:
        logger.warning(f"Unregistered pod {client_ip} attempted gh operation")
        raise HTTPException(403, "yolo-cage: pod not registered. Contact cluster admin.")

    cwd = translate_cwd(gh_req.cwd, assigned_branch)
    logger.info(f"gh from {client_ip} ({assigned_branch}): {gh_req.args}")

    return gh_handler.handle(gh_req.args, cwd)


# Pod lifecycle management endpoints
@app.post("/pods", response_model=PodCreateResponse)
async def create_pod(req: PodCreateRequest):
    """Create a new pod for a branch."""
    logger.info(f"Create pod requested for branch: {req.branch}")
    return handle_pod_operation("Failed to create pod", pods.create_pod, req.branch)


@app.get("/pods", response_model=PodListResponse)
async def list_pods():
    """List all yolo-cage pods."""
    pod_list = handle_pod_operation("Failed to list pods", pods.list_pods)
    return PodListResponse(pods=pod_list)


@app.get("/pods/{branch}", response_model=PodInfo)
async def get_pod(branch: str):
    """Get status of a specific pod."""
    def get_or_404():
        pod = pods.get_pod(branch)
        if pod is None:
            raise HTTPException(404, f"Pod for branch '{branch}' not found")
        return pod
    return handle_pod_operation("Failed to get pod", get_or_404)


@app.delete("/pods/{branch}")
async def delete_pod(branch: str, clean: bool = False):
    """Delete a pod. Use ?clean=true to also delete the workspace."""
    logger.info(f"Delete pod requested for branch: {branch} (clean={clean})")
    def delete_or_404():
        if not pods.delete_pod(branch, clean_workspace=clean):
            raise HTTPException(404, f"Pod for branch '{branch}' not found")
        return {"status": "deleted", "branch": branch, "workspace_cleaned": clean}
    return handle_pod_operation("Failed to delete pod", delete_or_404)
