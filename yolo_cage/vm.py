"""VM - Vagrant virtual machine operations."""

import subprocess
import sys
from pathlib import Path

from .output import die, log_step, log_success


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

    def sync_config(self, config_path: Path) -> None:
        """Copy config to VM and apply it."""
        log_step("Syncing configuration to VM...")
        self.ssh("mkdir -p ~/.yolo-cage")

        subprocess.run(
            ["vagrant", "ssh", "-c", "cat > ~/.yolo-cage/config.env"],
            cwd=self.repo_dir,
            input=config_path.read_text(),
            text=True,
            check=True,
        )

        log_step("Applying configuration...")
        self.ssh("yolo-cage-configure")

    def require_running(self) -> None:
        """Die if VM is not running."""
        if self.status != "running":
            die("VM is not running. Start with 'yolo-cage up'.")

    def require_exists(self) -> None:
        """Die if repo directory doesn't exist."""
        if not self.repo_dir.exists():
            die(f"Repository not found at {self.repo_dir}. Run 'yolo-cage build' first.")

    def _provider_args(self) -> list[str]:
        if sys.platform == "darwin":
            return ["--provider=qemu"]
        return []
