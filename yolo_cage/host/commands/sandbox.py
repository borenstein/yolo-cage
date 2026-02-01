"""Sandbox commands - create, attach, shell, list, delete, logs."""

import argparse
from pathlib import Path

from .. import instances, vagrant, config, github
from ...output import die, log_step, log_success


def _ensure_ready(args: argparse.Namespace) -> tuple[str, Path]:
    """Common setup: migrate, resolve instance, ensure VM running.

    Returns:
        Tuple of (instance_name, repo_dir)
    """
    instances.migrate_legacy()
    name = instances.resolve(args.instance)
    repo_dir = instances.get_repo_dir(name)

    if not (repo_dir / "Vagrantfile").exists():
        die(f"Repository not found for instance '{name}'.")

    vagrant.ensure_running(repo_dir, name)
    return name, repo_dir


def cmd_create(args: argparse.Namespace) -> None:
    """Create a sandbox for a branch."""
    name, repo_dir = _ensure_ready(args)
    config_path = instances.get_config_path(name)

    cfg = config.load_config(config_path)
    pat, repo_url = cfg.get("GITHUB_PAT"), cfg.get("REPO_URL")
    if not pat or not repo_url:
        die("Missing GITHUB_PAT or REPO_URL. Run 'yolo-cage configure'.")

    log_step("Validating repository access...")
    valid, message = github.validate_repo_access(repo_url, pat)
    if not valid:
        die(message)
    log_success(message)

    vagrant.ssh(repo_dir, f"yolo-cage-vm create '{args.branch}'", name)


def cmd_attach(args: argparse.Namespace) -> None:
    """Attach to a sandbox's Claude session."""
    name, repo_dir = _ensure_ready(args)
    vagrant.ssh(repo_dir, f"yolo-cage-vm attach '{args.branch}'", name, interactive=True)


def cmd_shell(args: argparse.Namespace) -> None:
    """Open a shell in a sandbox."""
    name, repo_dir = _ensure_ready(args)
    vagrant.ssh(repo_dir, f"yolo-cage-vm shell '{args.branch}'", name, interactive=True)


def cmd_list(args: argparse.Namespace) -> None:
    """List all sandboxes."""
    name, repo_dir = _ensure_ready(args)
    vagrant.ssh(repo_dir, "yolo-cage-vm list", name)


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a sandbox."""
    name, repo_dir = _ensure_ready(args)
    cmd = f"yolo-cage-vm delete '{args.branch}'"
    if args.clean:
        cmd += " --clean"
    vagrant.ssh(repo_dir, cmd, name)


def cmd_logs(args: argparse.Namespace) -> None:
    """Show sandbox logs."""
    name, repo_dir = _ensure_ready(args)
    vagrant.ssh(repo_dir, f"yolo-cage-vm logs '{args.branch}'", name)
