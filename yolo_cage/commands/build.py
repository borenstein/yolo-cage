"""Build command - set up yolo-cage instance."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from ..output import die, log_step, log_success, YELLOW, NC
from ..prerequisites import check_prerequisites
from ..instances import (
    create_instance,
    detect_local_repo,
    get_config_path,
    get_default_instance,
    get_instance_config,
    get_repo_dir,
    instance_exists,
    list_instances,
    set_default_instance,
)
from ..config import prompt_config
from ..vm import sync_config_to_vm, vagrant_provider_args


def cmd_build(args: argparse.Namespace) -> None:
    """Set up yolo-cage (clone repo, build VM)."""
    check_prerequisites()

    if sys.platform == "darwin":
        print()
        print(f"{YELLOW}Note: Apple Silicon support is experimental.{NC}")
        print("The vagrant-qemu plugin has known limitations.")
        print()

    # Determine instance name
    instances = list_instances()
    local_repo = detect_local_repo()

    if instances and not args.instance:
        die(
            "Instance already exists. Use --instance=<name> to create another.\n"
            f"Existing instances: {', '.join(instances)}"
        )

    instance_name = args.instance or "default"

    if instance_exists(instance_name):
        die(f"Instance '{instance_name}' already exists. Use a different name or destroy it first.")

    # Create instance - clone or use local repo
    # Check if local repo is already in use by another instance
    use_local_repo = False
    if local_repo:
        repo_in_use = False
        for existing in instances:
            existing_config = get_instance_config(existing)
            if existing_config.get("repo_path") == str(local_repo):
                repo_in_use = True
                break

        if repo_in_use:
            log_step(f"Local repo already in use by another instance, cloning instead...")
            use_local_repo = False
        else:
            log_step(f"Using local repository: {local_repo}")
            use_local_repo = True

    if use_local_repo:
        instance_dir = create_instance(instance_name, repo_path=local_repo)
    else:
        instance_dir = create_instance(instance_name)  # Will clone

    # If first instance, set as default
    if not get_default_instance():
        set_default_instance(instance_name)
        log_success(f"Instance '{instance_name}' set as default")

    # Handle config
    config_path = get_config_path(instance_name)
    existing_config = config_path.exists()

    if args.config_file:
        config_file = Path(args.config_file)
        if not config_file.exists():
            die(f"Config file not found: {config_file}")
        shutil.copy(config_file, config_path)
        log_success(f"Config copied to {config_path}")
    elif args.interactive:
        prompt_config(config_path)
    elif existing_config:
        log_success(f"Using existing config: {config_path}")
    else:
        die(
            f"No configuration found.\n\n"
            f"Either:\n"
            f"  - Run with --interactive to create one\n"
            f"  - Run with --config-file to use an existing file\n"
            f"  - Create {config_path} manually"
        )

    # Get repo directory for this instance
    repo_dir = get_repo_dir(instance_name)

    # Destroy existing VM if present
    vagrant_dir = repo_dir / ".vagrant"
    if vagrant_dir.exists():
        log_step("Destroying existing VM...")
        subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir)

    # Build VM
    log_step("Building VM (this may take a while)...")
    subprocess.run(["vagrant", "up"] + vagrant_provider_args(), cwd=repo_dir, check=True)

    # Sync config and apply
    sync_config_to_vm(repo_dir, config_path)

    if not args.up:
        subprocess.run(["vagrant", "halt"], cwd=repo_dir, check=True)
        print()
        log_success("VM built successfully!")
        print("Run 'yolo-cage up' to start the VM.")
    else:
        print()
        log_success("VM built and running!")
        print()
        print("Create a sandbox:  yolo-cage create <branch>")
        print("List sandboxes:    yolo-cage list")
        print("Attach to sandbox: yolo-cage attach <branch>")
