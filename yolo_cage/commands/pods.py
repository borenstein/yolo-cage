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
    """Format command with -I flag if not default instance."""
    default = get_default_instance()
    prefix = f"-I {instance} " if instance != default else ""
    return f"yolo-cage {prefix}{cmd}"


def _validate_config(config_path) -> tuple[str, str]:
    """Load and validate config, returning (pat, repo_url)."""
    config = load_config(config_path)
    pat, repo_url = config.get("GITHUB_PAT"), config.get("REPO_URL")
    if not pat or not repo_url:
        die("Missing GITHUB_PAT or REPO_URL. Run 'yolo-cage configure'.")

    log_step("Validating repository access...")
    valid, message = validate_github_repo(repo_url, pat)
    if not valid:
        die(message)
    log_success(message)
    return pat, repo_url


def cmd_create(args: argparse.Namespace) -> None:
    """Create a sandbox pod for a branch."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    ensure_vm_running(repo_dir)
    _validate_config(get_config_path(instance))

    vagrant_ssh(repo_dir, f"yolo-cage-inner create '{args.branch}'")
    print(f"Run: {_format_command(f'attach {args.branch}', instance)}")


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
