"""Sandbox operations - High-level operations for managing sandboxes."""

from typing import List

from ..common.errors import SandboxError
from ..common.logging import log_step, log_success
from ..domain.branch import Branch
from ..domain.sandbox import Sandbox
from . import kubernetes
from .dispatcher_client import DispatcherClient


def create_sandbox(branch: Branch) -> None:
    """Create a sandbox for a branch.

    Args:
        branch: Branch to create sandbox for

    Raises:
        SandboxError: If creation fails
    """
    pod_name = branch.to_pod_name()
    print(f"Creating sandbox for branch: {branch.name}")

    # Check if pod already exists
    if kubernetes.pod_exists(pod_name):
        raise SandboxError(f"Sandbox already exists for branch: {branch.name}")

    # Create via dispatcher
    client = DispatcherClient()
    try:
        response = client.create_sandbox(branch)
        message = response.get("message", response.get("status", "Pod created"))
        print(message)
    except Exception as e:
        raise SandboxError(f"Failed to create sandbox: {e}")

    # Wait for pod to be ready
    if response.get("status") in ["Pending", "Running"]:
        log_step("Waiting for sandbox to be ready...")
        try:
            kubernetes.wait_for_pod_ready(pod_name, timeout_seconds=120)
            print()
            log_success(f"Sandbox ready. Run: yolo-cage attach {branch.name}")
        except Exception as e:
            raise SandboxError(f"Sandbox creation timed out: {e}")


def list_sandboxes() -> List[Sandbox]:
    """List all sandboxes.

    Returns:
        List of Sandbox instances

    Raises:
        SandboxError: If listing fails
    """
    client = DispatcherClient()
    try:
        sandboxes = client.list_sandboxes()
        return sandboxes
    except Exception as e:
        raise SandboxError(f"Failed to list sandboxes: {e}")


def delete_sandbox(branch: Branch, clean: bool = False) -> None:
    """Delete a sandbox.

    Args:
        branch: Branch whose sandbox to delete
        clean: Whether to also delete workspace files

    Raises:
        SandboxError: If deletion fails
    """
    client = DispatcherClient()
    try:
        response = client.delete_sandbox(branch, clean=clean)
        status = response.get("status", "Deleted")
        print(status)
    except Exception as e:
        raise SandboxError(f"Failed to delete sandbox: {e}")


def attach_to_sandbox(branch: Branch) -> int:
    """Attach to a sandbox's Claude Code session.

    Args:
        branch: Branch whose sandbox to attach to

    Returns:
        Exit code from kubectl exec

    Raises:
        SandboxError: If attach fails
    """
    pod_name = branch.to_pod_name()
    print(f"Attaching to {pod_name}... (Ctrl+B,D to detach)")

    if not kubernetes.pod_exists(pod_name):
        raise SandboxError(f"Sandbox not found for branch: {branch.name}")

    # Attach to tmux session running Claude Code
    command = [
        "bash",
        "-c",
        'cd /home/dev/workspace && exec tmux new-session -A -s claude "claude --dangerously-skip-permissions"',
    ]

    try:
        return kubernetes.exec_in_pod(pod_name, command, interactive=True)
    except Exception as e:
        raise SandboxError(f"Failed to attach to sandbox: {e}")


def open_shell_in_sandbox(branch: Branch) -> int:
    """Open a shell in a sandbox.

    Args:
        branch: Branch whose sandbox to open shell in

    Returns:
        Exit code from kubectl exec

    Raises:
        SandboxError: If shell fails
    """
    pod_name = branch.to_pod_name()
    print(f"Opening shell in {pod_name}... (Ctrl+B,D to detach)")

    if not kubernetes.pod_exists(pod_name):
        raise SandboxError(f"Sandbox not found for branch: {branch.name}")

    # Open tmux session with bash
    command = [
        "bash",
        "-c",
        "cd /home/dev/workspace && exec tmux new-session -A -s shell",
    ]

    try:
        return kubernetes.exec_in_pod(pod_name, command, interactive=True)
    except Exception as e:
        raise SandboxError(f"Failed to open shell in sandbox: {e}")


def tail_sandbox_logs(branch: Branch) -> int:
    """Tail logs from a sandbox.

    Args:
        branch: Branch whose sandbox logs to tail

    Returns:
        Exit code from kubectl logs

    Raises:
        SandboxError: If tailing fails
    """
    pod_name = branch.to_pod_name()

    if not kubernetes.pod_exists(pod_name):
        raise SandboxError(f"Sandbox not found for branch: {branch.name}")

    try:
        return kubernetes.tail_pod_logs(pod_name)
    except Exception as e:
        raise SandboxError(f"Failed to tail sandbox logs: {e}")
