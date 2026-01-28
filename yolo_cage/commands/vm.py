"""VM lifecycle commands - up, down, destroy, status."""

import argparse
import subprocess

from ..output import die, log_step, log_success
from ..instances import (
    get_config_path,
    get_repo_dir,
    list_instances,
    get_default_instance,
    resolve_instance,
    maybe_migrate_legacy_layout,
)
from ..vm import get_vm_status, vagrant_provider_args, vagrant_ssh


def cmd_up(args: argparse.Namespace) -> None:
    """Start the VM."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    if not repo_dir.exists():
        die(f"Repository not found for instance '{instance}'. Run 'yolo-cage build' first.")

    if args.ram:
        print("Note: --ram option is not yet implemented. Using default RAM.")

    log_step(f"Starting VM for instance '{instance}'...")
    subprocess.run(["vagrant", "up"] + vagrant_provider_args(), cwd=repo_dir, check=True)

    log_success("VM is running")
    print()
    print("Create a sandbox:  yolo-cage create <branch>")
    print("List sandboxes:    yolo-cage list")


def cmd_down(args: argparse.Namespace) -> None:
    """Stop the VM."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    if not repo_dir.exists():
        die(f"Repository not found for instance '{instance}'.")

    log_step(f"Stopping VM for instance '{instance}'...")
    subprocess.run(["vagrant", "halt"], cwd=repo_dir, check=True)

    log_success("VM stopped")


def cmd_destroy(args: argparse.Namespace) -> None:
    """Remove the VM entirely."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)
    config_path = get_config_path(instance)

    if not repo_dir.exists():
        die(f"Repository not found for instance '{instance}'.")

    print(f"This will destroy the VM for instance '{instance}' and all data inside it.")
    print(f"Your config in {config_path} will be preserved.")
    print()
    confirm = input("Continue? [y/N] ").strip().lower()

    if confirm not in ("y", "yes"):
        print("Aborted.")
        return

    log_step("Destroying VM...")
    subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir, check=True)

    log_success("VM destroyed")


def _print_instance_status(name: str, is_default: bool) -> None:
    repo_dir = get_repo_dir(name)
    config_path = get_config_path(name)
    marker = " *" if is_default else ""

    print(f"Instance: {name}{marker}")
    print(f"  Repository: {repo_dir}")
    print(f"  Config: {config_path}")

    if not repo_dir.exists():
        print("  VM status: not built\n")
        return

    status = get_vm_status(repo_dir)
    print(f"  VM status: {status}")

    if status == "running":
        print("\n  Pods:")
        vagrant_ssh(repo_dir, "yolo-cage-inner list")
    print()


def cmd_status(args: argparse.Namespace) -> None:
    """Show VM and pod status."""
    maybe_migrate_legacy_layout()

    instances = list_instances()
    if not instances:
        print("No instances found.\nRun 'yolo-cage build --interactive --up' to get started.")
        return

    targets = [args.instance] if args.instance else instances
    default = get_default_instance()

    for name in targets:
        _print_instance_status(name, name == default)
