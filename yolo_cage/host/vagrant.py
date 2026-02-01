"""Vagrant VM operations."""

import subprocess
import sys
from pathlib import Path

from ..output import die, log_step


def provider_args() -> list[str]:
    """Return provider args for vagrant commands."""
    if sys.platform == "darwin":
        return ["--provider=qemu"]
    return []


def ssh(repo_dir: Path, command: str, interactive: bool = False) -> int:
    """Run command in VM via vagrant ssh."""
    if interactive:
        return subprocess.call(
            ["vagrant", "ssh", "--", "-t", command],
            cwd=repo_dir,
        )
    return subprocess.call(
        ["vagrant", "ssh", "-c", command],
        cwd=repo_dir,
    )


def get_status(repo_dir: Path) -> str:
    """Get VM status (running, poweroff, etc)."""
    result = subprocess.run(
        ["vagrant", "status", "--machine-readable"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if ",state," in line:
            return line.split(",")[3]
    return "unknown"


def ensure_running(repo_dir: Path) -> None:
    """Die if VM is not running."""
    if get_status(repo_dir) != "running":
        die("VM is not running. Start with 'yolo-cage up'.")


def sync_config(repo_dir: Path, config_path: Path) -> None:
    """Copy config to VM and apply it."""
    if not config_path.exists():
        die("No config found. Run 'yolo-cage build' with --interactive.")

    log_step("Syncing configuration to VM...")
    ssh(repo_dir, "mkdir -p ~/.yolo-cage")

    config_content = config_path.read_text()
    subprocess.run(
        ["vagrant", "ssh", "-c", "cat > ~/.yolo-cage/config.env"],
        cwd=repo_dir,
        input=config_content,
        text=True,
        check=True,
    )

    log_step("Applying configuration...")
    ssh(repo_dir, "yolo-cage-configure")
