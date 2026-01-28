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


def _validate_existing_config(config_path) -> None:
    """Validate an existing config file."""
    if not config_path.exists():
        die(f"No config at {config_path}. Run 'yolo-cage configure --interactive'.")

    config = load_config(config_path)
    pat, repo_url = config.get("GITHUB_PAT"), config.get("REPO_URL")
    if not pat or not repo_url:
        die("Missing GITHUB_PAT or REPO_URL in config.")

    log_step("Validating repository access...")
    valid, message = validate_github_repo(repo_url, pat)
    if not valid:
        die(message)
    log_success(message)


def _sync_if_running(repo_dir, config_path) -> None:
    """Sync config to VM if running, otherwise just report saved."""
    if not repo_dir.exists() or get_vm_status(repo_dir) != "running":
        log_success(f"Config saved to {config_path}")
        if repo_dir.exists():
            print("VM not running. Config will apply on next 'yolo-cage up'.")
        return

    sync_config_to_vm(repo_dir, config_path)


def cmd_configure(args: argparse.Namespace) -> None:
    """Update configuration and sync to VM."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    config_path = get_config_path(instance)
    repo_dir = get_repo_dir(instance)

    if args.interactive:
        prompt_config(config_path)
    else:
        _validate_existing_config(config_path)

    _sync_if_running(repo_dir, config_path)
