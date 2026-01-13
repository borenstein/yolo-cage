"""Git command classification."""

from enum import Enum
from typing import Optional


class CommandCategory(Enum):
    """Categories of git commands with different policy handling."""
    LOCAL = "local"           # No restrictions
    BRANCH = "branch"         # May warn about switching
    MERGE = "merge"           # Only on assigned branch
    REMOTE_READ = "remote_read"   # Allowed (fetch, pull)
    REMOTE_WRITE = "remote_write" # Branch enforcement + hooks
    DENIED = "denied"         # Blocked with message
    UNKNOWN = "unknown"       # Not recognized


ALLOWLIST_LOCAL = frozenset({
    "add", "rm", "mv", "status", "log", "diff", "show", "commit",
    "stash", "reset", "restore", "rev-parse", "ls-files",
    "blame", "shortlog", "describe", "tag", "clean",
})

ALLOWLIST_BRANCH = frozenset({"branch", "checkout", "switch"})

ALLOWLIST_MERGE = frozenset({"merge", "rebase", "cherry-pick"})

ALLOWLIST_REMOTE_READ = frozenset({"fetch", "pull"})

ALLOWLIST_REMOTE_WRITE = frozenset({"push"})

DENYLIST_MESSAGES = {
    "remote": "yolo-cage: remote management is not permitted",
    "clone": "yolo-cage: clone is not permitted; use the provided workspace",
    "submodule": "yolo-cage: submodules are not supported",
    "credential": "yolo-cage: credential management is not permitted",
    "config": (
        "yolo-cage: direct git configuration is not permitted.\n"
        "User identity and settings are managed via deployment configuration."
    ),
}


def get_subcommand(args: list[str]) -> Optional[str]:
    """Extract the git subcommand from args (first non-flag argument)."""
    for arg in args:
        if not arg.startswith("-"):
            return arg
    return None


def classify(args: list[str]) -> tuple[CommandCategory, Optional[str]]:
    """
    Classify a git command.

    Returns (category, deny_message). deny_message is only set for DENIED.
    """
    cmd = get_subcommand(args)
    if cmd is None:
        return CommandCategory.UNKNOWN, None

    if cmd in DENYLIST_MESSAGES:
        return CommandCategory.DENIED, DENYLIST_MESSAGES[cmd]

    if cmd in ALLOWLIST_LOCAL:
        return CommandCategory.LOCAL, None

    if cmd in ALLOWLIST_BRANCH:
        return CommandCategory.BRANCH, None

    if cmd in ALLOWLIST_MERGE:
        return CommandCategory.MERGE, None

    if cmd in ALLOWLIST_REMOTE_READ:
        return CommandCategory.REMOTE_READ, None

    if cmd in ALLOWLIST_REMOTE_WRITE:
        return CommandCategory.REMOTE_WRITE, None

    return CommandCategory.UNKNOWN, None
