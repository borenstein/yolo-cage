"""Vagrant VM operations."""

import subprocess
import sys
from pathlib import Path

from .output import die


def vagrant_provider_args() -> list[str]:
    """Return provider args for vagrant commands. macOS requires qemu."""
    if sys.platform == "darwin":
        return ["--provider=qemu"]
    return []


def vagrant_ssh(repo_dir: Path, command: str, interactive: bool = False) -> int:
    """Run a command inside the VM via vagrant ssh."""
    if interactive:
        return subprocess.call(
            ["vagrant", "ssh", "--", "-t", command],
            cwd=repo_dir,
        )
    else:
        return subprocess.call(
            ["vagrant", "ssh", "-c", command],
            cwd=repo_dir,
        )


def get_vm_status(repo_dir: Path) -> str:
    """Get the current VM status."""
    result = subprocess.run(
        ["vagrant", "status", "--machine-readable"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )

    status = "unknown"
    for line in result.stdout.splitlines():
        if ",state," in line:
            status = line.split(",")[3]
            break

    return status


def ensure_vm_running(repo_dir: Path) -> None:
    """Exit if VM is not running."""
    status = get_vm_status(repo_dir)

    if status != "running":
        die("VM is not running. Start with 'yolo-cage up'.")


def sync_config_to_vm(repo_dir: Path, config_path: Path) -> None:
    """Copy config to VM and apply it."""
    from .output import log_step

    if not config_path.exists():
        die("No config found. Run 'yolo-cage build' with --config-file or --interactive.")

    log_step("Syncing configuration to VM...")
    vagrant_ssh(repo_dir, "mkdir -p ~/.yolo-cage")

    # Copy config file content to VM
    config_content = config_path.read_text()
    subprocess.run(
        ["vagrant", "ssh", "-c", "cat > ~/.yolo-cage/config.env"],
        cwd=repo_dir,
        input=config_content,
        text=True,
        check=True,
    )

    log_step("Applying configuration...")
    vagrant_ssh(repo_dir, "yolo-cage-configure")
