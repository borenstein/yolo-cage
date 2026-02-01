"""Vagrant VM operations.

All functions that invoke Vagrant accept an instance_name parameter to identify
the Runtime. This is passed via YOLO_CAGE_INSTANCE environment variable so the
Vagrantfile can name the VM appropriately.
"""

import os
import subprocess
import sys
from pathlib import Path

from ..output import die, log_step


def _vagrant_env(instance_name: str) -> dict:
    """Return environment with YOLO_CAGE_INSTANCE set."""
    env = os.environ.copy()
    env["YOLO_CAGE_INSTANCE"] = instance_name
    return env


def provider_args() -> list[str]:
    """Return provider args for vagrant commands."""
    if sys.platform == "darwin":
        return ["--provider=qemu"]
    return []


def ssh(repo_dir: Path, command: str, instance_name: str = "default", interactive: bool = False) -> int:
    """Run command in VM via vagrant ssh."""
    env = _vagrant_env(instance_name)
    if interactive:
        return subprocess.call(
            ["vagrant", "ssh", "--", "-t", command],
            cwd=repo_dir,
            env=env,
        )
    return subprocess.call(
        ["vagrant", "ssh", "-c", command],
        cwd=repo_dir,
        env=env,
    )


def get_status(repo_dir: Path, instance_name: str = "default") -> str:
    """Get VM status (running, poweroff, etc)."""
    env = _vagrant_env(instance_name)
    result = subprocess.run(
        ["vagrant", "status", "--machine-readable"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        env=env,
    )
    for line in result.stdout.splitlines():
        if ",state," in line:
            return line.split(",")[3]
    return "unknown"


def ensure_running(repo_dir: Path, instance_name: str = "default") -> None:
    """Die if VM is not running."""
    if get_status(repo_dir, instance_name) != "running":
        die("VM is not running. Start with 'yolo-cage up'.")


def sync_config(repo_dir: Path, config_path: Path, instance_name: str = "default") -> None:
    """Copy config to VM and apply it."""
    if not config_path.exists():
        die("No config found. Run 'yolo-cage build' with --interactive.")

    env = _vagrant_env(instance_name)

    log_step("Syncing configuration to VM...")
    ssh(repo_dir, "mkdir -p ~/.yolo-cage", instance_name)

    config_content = config_path.read_text()
    subprocess.run(
        ["vagrant", "ssh", "-c", "cat > ~/.yolo-cage/config.env"],
        cwd=repo_dir,
        input=config_content,
        text=True,
        check=True,
        env=env,
    )

    log_step("Applying configuration...")
    ssh(repo_dir, "yolo-cage-configure", instance_name)


def up(repo_dir: Path, instance_name: str = "default") -> None:
    """Start the VM."""
    env = _vagrant_env(instance_name)
    subprocess.run(
        ["vagrant", "up"] + provider_args(),
        cwd=repo_dir,
        check=True,
        env=env,
    )


def halt(repo_dir: Path, instance_name: str = "default") -> None:
    """Stop the VM."""
    env = _vagrant_env(instance_name)
    subprocess.run(
        ["vagrant", "halt"],
        cwd=repo_dir,
        check=True,
        env=env,
    )


def destroy(repo_dir: Path, instance_name: str = "default") -> None:
    """Destroy the VM."""
    env = _vagrant_env(instance_name)
    subprocess.run(
        ["vagrant", "destroy", "-f"],
        cwd=repo_dir,
        check=True,
        env=env,
    )


def rsync(repo_dir: Path, instance_name: str = "default") -> None:
    """Sync files to VM."""
    env = _vagrant_env(instance_name)
    subprocess.run(
        ["vagrant", "rsync"],
        cwd=repo_dir,
        check=True,
        env=env,
    )
