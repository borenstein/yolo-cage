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


def _local_repo_available(local_repo: Path | None, instances: list[str]) -> bool:
    """Check if local repo can be used (exists and not already claimed)."""
    if not local_repo:
        return False
    for name in instances:
        if get_instance_config(name).get("repo_path") == str(local_repo):
            log_step("Local repo already in use, cloning instead...")
            return False
    log_step(f"Using local repository: {local_repo}")
    return True


def _setup_config(args: argparse.Namespace, config_path: Path) -> None:
    """Set up configuration from file, interactive prompt, or existing."""
    if args.config_file:
        src = Path(args.config_file)
        if not src.exists():
            die(f"Config file not found: {src}")
        shutil.copy(src, config_path)
        log_success(f"Config copied to {config_path}")
        return

    if args.interactive:
        prompt_config(config_path)
        return

    if config_path.exists():
        log_success(f"Using existing config: {config_path}")
        return

    die(
        f"No configuration found.\n\n"
        f"Either:\n"
        f"  - Run with --interactive to create one\n"
        f"  - Run with --config-file to use an existing file\n"
        f"  - Create {config_path} manually"
    )


def cmd_build(args: argparse.Namespace) -> None:
    """Set up yolo-cage (clone repo, build VM)."""
    check_prerequisites()

    if sys.platform == "darwin":
        print(f"\n{YELLOW}Note: Apple Silicon support is experimental.{NC}")
        print("The vagrant-qemu plugin has known limitations.\n")

    instances = list_instances()
    if instances and not args.instance:
        die(f"Instance already exists. Use --instance=<name> to create another.\n"
            f"Existing instances: {', '.join(instances)}")

    instance_name = args.instance or "default"
    if instance_exists(instance_name):
        die(f"Instance '{instance_name}' already exists.")

    local_repo = detect_local_repo()
    use_local = _local_repo_available(local_repo, instances)
    create_instance(instance_name, repo_path=local_repo if use_local else None)

    if not get_default_instance():
        set_default_instance(instance_name)
        log_success(f"Instance '{instance_name}' set as default")

    config_path = get_config_path(instance_name)
    _setup_config(args, config_path)

    repo_dir = get_repo_dir(instance_name)
    if (repo_dir / ".vagrant").exists():
        log_step("Destroying existing VM...")
        subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir)

    log_step("Building VM (this may take a while)...")
    subprocess.run(["vagrant", "up"] + vagrant_provider_args(), cwd=repo_dir, check=True)
    sync_config_to_vm(repo_dir, config_path)

    if args.up:
        print("\n")
        log_success("VM built and running!")
        print("\nCreate a sandbox:  yolo-cage create <branch>")
        print("List sandboxes:    yolo-cage list")
        print("Attach to sandbox: yolo-cage attach <branch>")
    else:
        subprocess.run(["vagrant", "halt"], cwd=repo_dir, check=True)
        print("\n")
        log_success("VM built successfully!")
        print("Run 'yolo-cage up' to start the VM.")
