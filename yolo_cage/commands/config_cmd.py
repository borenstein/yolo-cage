"""Configuration command."""

import argparse

from ..output import die, log_step, log_success
from ..instances import (
    get_config_path,
    get_repo_dir,
    resolve_instance,
    maybe_migrate_legacy_layout,
)
from ..config import load_config, prompt_config
from ..github import validate_github_repo
from ..vm import get_vm_status, sync_config_to_vm


def cmd_configure(args: argparse.Namespace) -> None:
    """Update configuration and sync to VM."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    config_path = get_config_path(instance)
    repo_dir = get_repo_dir(instance)

    if args.interactive:
        prompt_config(config_path)
    else:
        if not config_path.exists():
            die(f"No config found at {config_path}\nRun 'yolo-cage configure --interactive' to create one.")

        # Validate the config before syncing
        config = load_config(config_path)
        pat = config.get("GITHUB_PAT")
        repo_url = config.get("REPO_URL")

        if not pat or not repo_url:
            die("Missing GITHUB_PAT or REPO_URL in config.")

        log_step("Validating repository access...")
        valid, message = validate_github_repo(repo_url, pat)
        if not valid:
            die(message)
        log_success(message)

    # Sync to VM if it's running
    if repo_dir.exists():
        vm_status = get_vm_status(repo_dir)

        if vm_status == "running":
            sync_config_to_vm(repo_dir, config_path)
        else:
            log_success(f"Config saved to {config_path}")
            print("VM is not running. Config will be applied on next 'yolo-cage up'.")
    else:
        log_success(f"Config saved to {config_path}")
