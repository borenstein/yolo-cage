"""Branch enforcement policy."""

from typing import Optional

from .commands import get_subcommand
from .git import get_current_branch


def get_checkout_target(args: list[str]) -> Optional[str]:
    """
    Extract the target branch from a checkout/switch command.

    Returns the branch name, or None if not switching branches.
    """
    cmd = get_subcommand(args)
    if cmd not in ("checkout", "switch"):
        return None

    # Find the argument after 'checkout' or 'switch' that isn't a flag
    found_cmd = False
    for arg in args:
        if arg in ("checkout", "switch"):
            found_cmd = True
            continue
        if found_cmd and not arg.startswith("-"):
            return arg

    return None


def check_branch_switch(args: list[str], assigned_branch: str) -> Optional[str]:
    """
    Check if a branch switch command is switching away from assigned branch.

    Returns a warning message if switching away, None otherwise.
    """
    target = get_checkout_target(args)
    if target is None or target == assigned_branch:
        return None

    return (
        f"yolo-cage: you are now viewing branch '{target}'.\n"
        f"Your assigned branch is '{assigned_branch}'.\n"
        f"Commits and pushes to other branches are not permitted.\n"
    )


def check_merge_allowed(cwd: str, assigned_branch: str, cmd: str) -> Optional[str]:
    """
    Check if a merge/rebase/cherry-pick is allowed.

    Returns an error message if not allowed, None if allowed.
    """
    current = get_current_branch(cwd)
    if current == assigned_branch:
        return None

    return (
        f"yolo-cage: you can only {cmd} while on your assigned branch "
        f"'{assigned_branch}'.\nRun 'git checkout {assigned_branch}' first.\n"
    )


def get_push_refspec_target(args: list[str]) -> Optional[str]:
    """
    Extract the remote branch target from a push refspec.

    For 'git push origin local:remote', returns 'remote'.
    Returns None if no explicit refspec.
    """
    for arg in args:
        if ":" in arg and not arg.startswith("-"):
            _, remote_ref = arg.split(":", 1)
            return remote_ref if remote_ref else None
    return None


def check_push_allowed(
    args: list[str],
    cwd: str,
    assigned_branch: str,
) -> Optional[str]:
    """
    Check if a push is allowed.

    Returns an error message if not allowed, None if allowed.
    """
    # Must be on assigned branch
    current = get_current_branch(cwd)
    if current != assigned_branch:
        return (
            f"yolo-cage: you can only push from your assigned branch "
            f"'{assigned_branch}'.\nCurrent branch is '{current}'.\n"
        )

    # Cannot push to a different remote branch
    refspec_target = get_push_refspec_target(args)
    if refspec_target and refspec_target != assigned_branch:
        return f"yolo-cage: you can only push to branch '{assigned_branch}'\n"

    return None
