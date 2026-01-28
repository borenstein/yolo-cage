"""Instance management commands - instances, set-default, upgrade."""

import argparse
import os
import subprocess
import tempfile
import urllib.request

from ..output import die, log_step, log_success, log_error
from ..instances import (
    get_config_path,
    get_default_instance,
    get_instance_config,
    get_repo_dir,
    instance_exists,
    list_instances,
    maybe_migrate_legacy_layout,
    set_default_instance,
)
from ..vm import sync_config_to_vm, vagrant_provider_args
from .. import __version__

CLI_URL = "https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage"
CLI_PATH = "/usr/local/bin/yolo-cage"


def cmd_instances(args: argparse.Namespace) -> None:
    """List all instances."""
    maybe_migrate_legacy_layout()

    instances = list_instances()
    if not instances:
        print("No instances found.")
        print()
        print("Run 'yolo-cage build --interactive --up' to create one.")
        return

    default = get_default_instance()

    print("Instances:")
    for name in instances:
        marker = " *" if name == default else ""
        print(f"  {name}{marker}")

    print()
    print("* = default instance")


def cmd_set_default(args: argparse.Namespace) -> None:
    """Set the default instance."""
    maybe_migrate_legacy_layout()

    name = args.name
    if not instance_exists(name):
        instances = list_instances()
        if instances:
            die(f"Instance '{name}' does not exist.\nAvailable instances: {', '.join(instances)}")
        else:
            die(f"Instance '{name}' does not exist. No instances found.")

    set_default_instance(name)
    log_success(f"Default instance set to '{name}'")


def _download_cli() -> None:
    """Download and install latest CLI binary."""
    log_step("Downloading latest CLI...")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        try:
            urllib.request.urlretrieve(CLI_URL, tmp.name)
            os.chmod(tmp.name, 0o755)
            subprocess.run(["sudo", "cp", tmp.name, CLI_PATH], check=True)
            log_success("CLI updated")
        finally:
            os.unlink(tmp.name)


def _update_repo(instance: str) -> None:
    """Pull latest for cloned repo instances."""
    config = get_instance_config(instance)
    if config.get("repo_path"):
        print(f"Skipping repo update for '{instance}' (local repo)")
        return

    repo_dir = get_repo_dir(instance)
    if not repo_dir.exists():
        return

    log_step(f"Updating repository for '{instance}'...")
    subprocess.run(["git", "fetch", "origin"], cwd=repo_dir, capture_output=True)
    result = subprocess.run(
        ["git", "reset", "--hard", "origin/main"],
        cwd=repo_dir, capture_output=True, text=True,
    )
    if result.returncode == 0:
        log_success("Repository updated")
    else:
        log_error(f"Failed: {result.stderr}")


def _rebuild_vm(instance: str) -> None:
    """Destroy and recreate VM."""
    repo_dir = get_repo_dir(instance)
    config_path = get_config_path(instance)

    if not repo_dir.exists():
        die(f"No repository for '{instance}'. Run 'yolo-cage build' first.")

    log_step(f"Rebuilding VM for '{instance}'...")
    subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir)
    subprocess.run(["vagrant", "up"] + vagrant_provider_args(), cwd=repo_dir, check=True)
    sync_config_to_vm(repo_dir, config_path)
    log_success("VM rebuilt")


def cmd_upgrade(args: argparse.Namespace) -> None:
    """Upgrade yolo-cage to the latest version."""
    maybe_migrate_legacy_layout()

    instance = args.instance or get_default_instance()

    _download_cli()

    if instance:
        _update_repo(instance)
        if args.rebuild:
            _rebuild_vm(instance)
        else:
            print("\nRun 'yolo-cage build' to update the VM.")


def cmd_version(args: argparse.Namespace) -> None:
    """Show version."""
    print(f"yolo-cage {__version__}")
