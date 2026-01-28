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


def _warn_darwin() -> None:
    if sys.platform == "darwin":
        print(f"\n{YELLOW}Note: Apple Silicon support is experimental.{NC}")
        print("The vagrant-qemu plugin has known limitations.\n")


def _resolve_instance_name(args: argparse.Namespace) -> str:
    instances = list_instances()
    if instances and not args.instance:
        die(f"Instance exists. Use --instance=<name>.\nExisting: {', '.join(instances)}")

    name = args.instance or "default"
    if instance_exists(name):
        die(f"Instance '{name}' already exists.")
    return name


def _choose_repo_path(instances: list[str]) -> Path | None:
    local = detect_local_repo()
    if not local:
        return None
    for name in instances:
        if get_instance_config(name).get("repo_path") == str(local):
            log_step("Local repo in use, cloning instead...")
            return None
    log_step(f"Using local repository: {local}")
    return local


def _setup_config(args: argparse.Namespace, config_path: Path) -> None:
    if args.config_file:
        src = Path(args.config_file)
        if not src.exists():
            die(f"Config file not found: {src}")
        shutil.copy(src, config_path)
        log_success(f"Config copied to {config_path}")
    elif args.interactive:
        prompt_config(config_path)
    elif config_path.exists():
        log_success(f"Using existing config: {config_path}")
    else:
        die(f"No config. Use --interactive or --config-file.")


def _destroy_existing_vm(repo_dir: Path) -> None:
    if (repo_dir / ".vagrant").exists():
        log_step("Destroying existing VM...")
        subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir)


def _build_vm(repo_dir: Path, config_path: Path) -> None:
    log_step("Building VM (this may take a while)...")
    subprocess.run(["vagrant", "up"] + vagrant_provider_args(), cwd=repo_dir, check=True)
    sync_config_to_vm(repo_dir, config_path)


def _finalize(repo_dir: Path, keep_running: bool) -> None:
    if keep_running:
        log_success("VM built and running!")
        print("Create a sandbox:  yolo-cage create <branch>")
        print("List sandboxes:    yolo-cage list")
        print("Attach to sandbox: yolo-cage attach <branch>")
    else:
        subprocess.run(["vagrant", "halt"], cwd=repo_dir, check=True)
        log_success("VM built successfully!")
        print("Run 'yolo-cage up' to start the VM.")


def cmd_build(args: argparse.Namespace) -> None:
    """Set up yolo-cage (clone repo, build VM)."""
    check_prerequisites()
    _warn_darwin()

    name = _resolve_instance_name(args)
    repo_path = _choose_repo_path(list_instances())
    create_instance(name, repo_path=repo_path)

    if not get_default_instance():
        set_default_instance(name)
        log_success(f"Instance '{name}' set as default")

    config_path = get_config_path(name)
    _setup_config(args, config_path)

    repo_dir = get_repo_dir(name)
    _destroy_existing_vm(repo_dir)
    _build_vm(repo_dir, config_path)
    _finalize(repo_dir, args.up)
