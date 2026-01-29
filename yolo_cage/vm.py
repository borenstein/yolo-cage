"""VM - Vagrant virtual machine operations."""

import subprocess
import sys
from pathlib import Path

from .errors import VMNotRunning, VMNotFound


class VM:
    """A Vagrant-managed virtual machine."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir

    @property
    def status(self) -> str:
        """Get VM status: running, poweroff, not_created, etc."""
        if not self.repo_dir.exists():
            return "not_created"

        result = subprocess.run(
            ["vagrant", "status", "--machine-readable"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if ",state," in line:
                return line.split(",")[3]
        return "unknown"

    def start(self) -> None:
        """Start the VM."""
        subprocess.run(
            ["vagrant", "up"] + self._provider_args(),
            cwd=self.repo_dir,
            check=True,
        )

    def stop(self) -> None:
        """Stop the VM."""
        subprocess.run(["vagrant", "halt"], cwd=self.repo_dir, check=True)

    def destroy(self, force: bool = True) -> None:
        """Destroy the VM."""
        cmd = ["vagrant", "destroy"]
        if force:
            cmd.append("-f")
        subprocess.run(cmd, cwd=self.repo_dir, check=True)

    def ssh(self, command: str, interactive: bool = False) -> int:
        """Run a command in the VM. Returns exit code."""
        if interactive:
            return subprocess.call(
                ["vagrant", "ssh", "--", "-t", command],
                cwd=self.repo_dir,
            )
        return subprocess.call(
            ["vagrant", "ssh", "-c", command],
            cwd=self.repo_dir,
        )

    def require_running(self) -> None:
        """Raise VMNotRunning if VM is not running."""
        if self.status != "running":
            raise VMNotRunning("VM is not running. Start with 'yolo-cage up'.")

    def require_exists(self) -> None:
        """Raise VMNotFound if repo directory doesn't exist."""
        if not self.repo_dir.exists():
            raise VMNotFound(f"Repository not found at {self.repo_dir}. Run 'yolo-cage build' first.")

    def _provider_args(self) -> list[str]:
        """Return provider arguments for vagrant up."""
        if sys.platform == "darwin":
            return ["--provider=qemu"]
        return []
