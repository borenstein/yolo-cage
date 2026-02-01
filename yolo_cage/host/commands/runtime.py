"""Runtime lifecycle commands - up, down, destroy, status."""

import argparse
import subprocess

from .. import instances, vagrant
from ...output import die, log_step, log_success


def cmd_up(args: argparse.Namespace) -> None:
    """Start the VM."""
    instances.migrate_legacy()
    name = instances.resolve(args.instance)
    repo_dir = instances.get_repo_dir(name)

    if not (repo_dir / "Vagrantfile").exists():
        die(f"Repository not found for instance '{name}'. Run 'yolo-cage build' first.")

    log_step(f"Starting VM for '{name}'...")
    subprocess.run(["vagrant", "up"] + vagrant.provider_args(), cwd=repo_dir, check=True)

    log_success("VM is running")
    print()
    print("Create a sandbox:  yolo-cage create <branch>")
    print("List sandboxes:    yolo-cage list")


def cmd_down(args: argparse.Namespace) -> None:
    """Stop the VM."""
    instances.migrate_legacy()
    name = instances.resolve(args.instance)
    repo_dir = instances.get_repo_dir(name)

    if not (repo_dir / "Vagrantfile").exists():
        die(f"Repository not found for instance '{name}'.")

    log_step(f"Stopping VM for '{name}'...")
    subprocess.run(["vagrant", "halt"], cwd=repo_dir, check=True)
    log_success("VM stopped")


def cmd_destroy(args: argparse.Namespace) -> None:
    """Destroy the VM (keeps instance and config)."""
    instances.migrate_legacy()
    name = instances.resolve(args.instance)
    repo_dir = instances.get_repo_dir(name)
    config_path = instances.get_config_path(name)

    print(f"This will destroy the VM for '{name}'.")
    print(f"Config at {config_path} will be preserved.")
    confirm = input("Continue? [y/N] ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted.")
        return

    log_step("Destroying VM...")
    subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir, check=True)
    log_success("VM destroyed")


def cmd_status(args: argparse.Namespace) -> None:
    """Show instance and VM status."""
    instances.migrate_legacy()
    name = instances.resolve(args.instance)
    repo_dir = instances.get_repo_dir(name)
    config_path = instances.get_config_path(name)

    if not (repo_dir / "Vagrantfile").exists():
        print(f"Instance: {name}")
        print("Status: Not built")
        print()
        print("Run 'yolo-cage build --interactive' to set up.")
        return

    status = vagrant.get_status(repo_dir)

    print(f"Instance: {name}")
    print(f"Repository: {repo_dir}")
    print(f"Config: {config_path}")
    print(f"VM: {status}")

    if status == "running":
        print()
        print("Sandboxes:", flush=True)
        vagrant.ssh(repo_dir, "yolo-cage-vm list")
