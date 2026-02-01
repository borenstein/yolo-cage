"""Build command - set up yolo-cage instance."""

import argparse
import shutil
import subprocess
import sys

from .. import instances, vagrant, config, prerequisites
from ...output import die, log_step, log_success


def cmd_build(args: argparse.Namespace) -> None:
    """Set up yolo-cage (create instance, clone repo, build VM)."""
    # Check prerequisites
    missing = prerequisites.check()
    if missing:
        prerequisites.print_install_help(missing)
        sys.exit(1)

    if sys.platform == "darwin":
        print("\nNote: Apple Silicon support is experimental.\n")

    instances.migrate_legacy()

    # Determine instance name and repo path
    name = args.instance or "default"
    dev_repo = instances.detect_dev_repo()

    # Create or use existing instance
    if instances.instance_exists(name):
        log_step(f"Using existing instance: {name}")
    else:
        log_step(f"Creating instance: {name}")
        instances.create(name, repo_path=dev_repo)

    instance_dir = instances.get_instance_dir(name)
    config_path = instances.get_config_path(name)
    repo_dir = instances.get_repo_dir(name)

    # Handle configuration
    if args.config_file:
        src = args.config_file
        if not src.exists():
            die(f"Config file not found: {src}")
        instance_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, config_path)
        log_success(f"Config copied to {config_path}")
    elif args.interactive:
        config.prompt_config(config_path)
    elif config_path.exists():
        log_success(f"Using existing config: {config_path}")
    else:
        die(
            "No configuration found.\n\n"
            "Either:\n"
            "  - Run with --interactive to create one\n"
            "  - Run with --config-file to use an existing file\n"
            f"  - Create {config_path} manually"
        )

    # Destroy existing VM if present
    if (repo_dir / ".vagrant").exists():
        log_step("Destroying existing VM...")
        subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir)

    # Build VM
    log_step("Building VM (this may take a while)...")
    subprocess.run(
        ["vagrant", "up"] + vagrant.provider_args(),
        cwd=repo_dir,
        check=True,
    )

    # Sync config
    vagrant.sync_config(repo_dir, config_path)

    # Set as default if only instance
    if len(instances.list_instances()) == 1:
        instances.set_default(name)

    if not args.up:
        subprocess.run(["vagrant", "halt"], cwd=repo_dir, check=True)
        print()
        log_success(f"Instance '{name}' built!")
        print("Run 'yolo-cage up' to start.")
    else:
        print()
        log_success(f"Instance '{name}' built and running!")
        print()
        print("Create a sandbox:  yolo-cage create <branch>")
        print("List sandboxes:    yolo-cage list")
