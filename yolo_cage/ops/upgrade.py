"""Upgrade workflow for yolo-cage."""

import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from ..core import Instance
from .build import sync_config


CLI_URL = "https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage"


def upgrade_cli(target_path: Path) -> None:
    """Download and install latest CLI binary."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        try:
            urllib.request.urlretrieve(CLI_URL, tmp.name)
            os.chmod(tmp.name, 0o755)
            subprocess.run(["sudo", "cp", tmp.name, str(target_path)], check=True)
        finally:
            os.unlink(tmp.name)


def upgrade_repo(instance: Instance) -> bool:
    """Update instance repo from origin. Returns True if updated."""
    if instance._repo_path:
        return False  # Local repo, skip

    if not instance.repo_dir.exists():
        return False

    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=instance.repo_dir,
        capture_output=True,
    )
    subprocess.run(
        ["git", "reset", "--hard", "origin/main"],
        cwd=instance.repo_dir,
        capture_output=True,
    )
    return True


def rebuild_vm(instance: Instance) -> None:
    """Destroy and rebuild VM, then sync config."""
    instance.vm.destroy()
    instance.vm.start()
    sync_config(instance)
