"""Instance management commands - instances, set-default, upgrade."""

import argparse
import os
import shutil
import subprocess
import tempfile
import urllib.request

from ..output import die, log_step, log_success, log_error
from ..instances import (
    get_default_instance,
    get_repo_dir,
    get_yolo_cage_home,
    instance_exists,
    list_instances,
    maybe_migrate_legacy_layout,
    set_default_instance,
)
from ..vm import sync_config_to_vm, vagrant_provider_args
from ..config import load_config
from .. import __version__


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


def cmd_upgrade(args: argparse.Namespace) -> None:
    """Upgrade yolo-cage to the latest version."""
    maybe_migrate_legacy_layout()

    # Determine which instance to upgrade (if any)
    instances = list_instances()
    instance = args.instance
    if not instance and instances:
        instance = get_default_instance()

    # Step 1: Update the CLI binary
    log_step("Downloading latest yolo-cage CLI...")
    cli_url = "https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage"

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            urllib.request.urlretrieve(cli_url, tmp.name)
            tmp_path = tmp.name

        # Make executable and move to /usr/local/bin
        os.chmod(tmp_path, 0o755)
        target = "/usr/local/bin/yolo-cage"

        # Try to copy (may need sudo)
        try:
            shutil.copy(tmp_path, target)
            log_success("CLI updated")
        except PermissionError:
            print(f"Need sudo to update {target}")
            result = subprocess.run(["sudo", "cp", tmp_path, target])
            if result.returncode == 0:
                log_success("CLI updated")
            else:
                die("Failed to update CLI")
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        die(f"Failed to download CLI: {e}")

    # Step 2: Update repos for instances with cloned repos
    if instance:
        from ..instances import get_instance_config, get_config_path

        config = get_instance_config(instance)
        if config.get("repo_path") is None:
            # This is a cloned repo, update it
            repo_dir = get_repo_dir(instance)
            if repo_dir.exists():
                log_step(f"Updating repository for instance '{instance}'...")
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=repo_dir,
                    capture_output=True,
                )
                result = subprocess.run(
                    ["git", "reset", "--hard", "origin/main"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    log_success("Repository updated")
                else:
                    log_error(f"Failed to update repository: {result.stderr}")
        else:
            print(f"Skipping repo update for instance '{instance}' (uses local repo)")

    # Step 3: Optionally rebuild VM
    if args.rebuild and instance:
        repo_dir = get_repo_dir(instance)
        config_path = get_config_path(instance)

        if not repo_dir.exists():
            die(f"No repository found for instance '{instance}'. Run 'yolo-cage build' first.")

        log_step(f"Rebuilding VM for instance '{instance}'...")
        subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir)
        subprocess.run(["vagrant", "up"] + vagrant_provider_args(), cwd=repo_dir, check=True)
        sync_config_to_vm(repo_dir, config_path)
        log_success("VM rebuilt")
    elif not args.rebuild:
        print()
        print("CLI and repo updated. Run 'yolo-cage build' to update the VM.")


def cmd_version(args: argparse.Namespace) -> None:
    """Show version."""
    print(f"yolo-cage {__version__}")
