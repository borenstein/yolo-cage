"""Pod management commands - create, attach, shell, list, delete, logs."""

import argparse

from ..output import die, log_step, log_success
from ..instances import (
    get_config_path,
    get_default_instance,
    get_repo_dir,
    resolve_instance,
    maybe_migrate_legacy_layout,
)
from ..config import load_config
from ..github import validate_github_repo
from ..vm import ensure_vm_running, vagrant_ssh


def _format_command(cmd: str, instance: str) -> str:
    """Format a yolo-cage command, including -I flag if not default instance."""
    default = get_default_instance()
    if instance != default:
        return f"yolo-cage -I {instance} {cmd}"
    return f"yolo-cage {cmd}"


def cmd_create(args: argparse.Namespace) -> None:
    """Create a sandbox pod for a branch."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)
    config_path = get_config_path(instance)

    ensure_vm_running(repo_dir)

    # Validate repository access before creating pod
    config = load_config(config_path)
    pat = config.get("GITHUB_PAT")
    repo_url = config.get("REPO_URL")

    if not pat or not repo_url:
        die("Missing GITHUB_PAT or REPO_URL in config. Run 'yolo-cage configure'.")

    log_step("Validating repository access...")
    valid, message = validate_github_repo(repo_url, pat)
    if not valid:
        die(message)
    log_success(message)

    vagrant_ssh(repo_dir, f"yolo-cage-inner create '{args.branch}'")

    # Print attach command with proper instance context
    attach_cmd = _format_command(f"attach {args.branch}", instance)
    print(f"Run: {attach_cmd}")


def cmd_attach(args: argparse.Namespace) -> None:
    """Attach to a sandbox pod (tmux session)."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    ensure_vm_running(repo_dir)
    vagrant_ssh(repo_dir, f"yolo-cage-inner attach '{args.branch}'", interactive=True)


def cmd_shell(args: argparse.Namespace) -> None:
    """Open a shell in a sandbox pod."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    ensure_vm_running(repo_dir)
    vagrant_ssh(repo_dir, f"yolo-cage-inner shell '{args.branch}'", interactive=True)


def cmd_list(args: argparse.Namespace) -> None:
    """List all sandbox pods."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    ensure_vm_running(repo_dir)
    vagrant_ssh(repo_dir, "yolo-cage-inner list")


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a sandbox pod."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    ensure_vm_running(repo_dir)

    cmd = f"yolo-cage-inner delete '{args.branch}'"
    if args.clean:
        cmd += " --clean"

    vagrant_ssh(repo_dir, cmd)


def cmd_logs(args: argparse.Namespace) -> None:
    """Tail pod logs."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    ensure_vm_running(repo_dir)
    vagrant_ssh(repo_dir, f"yolo-cage-inner logs '{args.branch}'")
