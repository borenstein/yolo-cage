"""Configure command."""

import argparse

from .. import instances, vagrant, config, github
from ...output import die, log_step, log_success


def cmd_configure(args: argparse.Namespace) -> None:
    """Update configuration and sync to VM."""
    instances.migrate_legacy()
    name = instances.resolve(args.instance)
    config_path = instances.get_config_path(name)
    repo_dir = instances.get_repo_dir(name)

    if args.interactive:
        config.prompt_config(config_path)
    else:
        if not config_path.exists():
            die(f"No config at {config_path}. Run with --interactive.")

        cfg = config.load_config(config_path)
        pat, repo_url = cfg.get("GITHUB_PAT"), cfg.get("REPO_URL")
        if not pat or not repo_url:
            die("Missing GITHUB_PAT or REPO_URL in config.")

        log_step("Validating repository access...")
        valid, message = github.validate_repo_access(repo_url, pat)
        if not valid:
            die(message)
        log_success(message)

    # Sync to VM if running
    if (repo_dir / "Vagrantfile").exists():
        status = vagrant.get_status(repo_dir)
        if status == "running":
            vagrant.sync_config(repo_dir, config_path)
        else:
            log_success(f"Config saved to {config_path}")
            print("VM not running. Config will apply on next 'yolo-cage up'.")
    else:
        log_success(f"Config saved to {config_path}")
