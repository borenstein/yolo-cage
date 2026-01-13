"""GitHub CLI command classification.

Mirrors the approach in commands.py for git commands.
"""

from enum import Enum
from typing import Optional


class GhCommandCategory(Enum):
    """Categories of gh commands with different policy handling."""
    ALLOWED = "allowed"         # Permitted operations
    BLOCKED = "blocked"         # Blocked with message
    UNKNOWN = "unknown"         # Not recognized - blocked by default


# Subcommands that are allowed
# Format: {main_command: {subcommands}} or {main_command: None} for all subcommands
ALLOWED_COMMANDS: dict[str, Optional[set[str]]] = {
    # Issue operations - all allowed
    "issue": {"create", "list", "view", "comment", "edit", "status", "close", "reopen"},

    # PR operations - most allowed, merge blocked separately
    "pr": {"create", "list", "view", "comment", "edit", "diff", "checks", "status", "checkout", "close"},

    # Repo read operations
    "repo": {"view", "list", "clone"},

    # Search is read-only
    "search": {"issues", "prs", "repos", "code", "commits"},

    # Gist operations
    "gist": {"create", "list", "view", "edit"},

    # Browse (opens URLs, harmless)
    "browse": None,  # All subcommands

    # Status
    "status": None,

    # Workflow viewing (not triggering)
    "run": {"list", "view", "watch"},

    # Label operations
    "label": {"list", "create", "edit"},

    # Project operations (read + basic write)
    "project": {"list", "view", "create", "edit", "field-list", "item-list", "item-add"},
}

# Subcommands that are explicitly blocked with specific messages
BLOCKED_COMMANDS: dict[str, dict[str, str]] = {
    "pr": {
        "merge": "yolo-cage: merging PRs is not permitted. Open a PR for human review instead.",
    },
    "repo": {
        "delete": "yolo-cage: deleting repositories is not permitted.",
        "create": "yolo-cage: creating repositories is not permitted.",
        "edit": "yolo-cage: editing repository settings is not permitted.",
        "rename": "yolo-cage: renaming repositories is not permitted.",
        "archive": "yolo-cage: archiving repositories is not permitted.",
    },
    "release": {
        "delete": "yolo-cage: deleting releases is not permitted.",
    },
    "secret": {
        # All secret operations blocked
        "set": "yolo-cage: managing secrets is not permitted.",
        "delete": "yolo-cage: managing secrets is not permitted.",
        "list": "yolo-cage: accessing secrets is not permitted.",
    },
    "ssh-key": {
        "add": "yolo-cage: managing SSH keys is not permitted.",
        "delete": "yolo-cage: managing SSH keys is not permitted.",
        "list": "yolo-cage: listing SSH keys is not permitted.",
    },
    "gpg-key": {
        "add": "yolo-cage: managing GPG keys is not permitted.",
        "delete": "yolo-cage: managing GPG keys is not permitted.",
    },
    "auth": {
        # All auth operations blocked - we manage auth
        "login": "yolo-cage: authentication is managed by the sandbox.",
        "logout": "yolo-cage: authentication is managed by the sandbox.",
        "setup-git": "yolo-cage: git authentication is managed by the sandbox.",
        "refresh": "yolo-cage: authentication is managed by the sandbox.",
    },
    "config": {
        # Config operations blocked
        "set": "yolo-cage: gh configuration is managed by the sandbox.",
        "clear-cache": "yolo-cage: gh configuration is managed by the sandbox.",
    },
    "variable": {
        # Variable operations blocked (like secrets)
        "set": "yolo-cage: managing variables is not permitted.",
        "delete": "yolo-cage: managing variables is not permitted.",
        "list": "yolo-cage: accessing variables is not permitted.",
    },
}

# Commands blocked entirely (all subcommands)
FULLY_BLOCKED_COMMANDS: dict[str, str] = {
    "api": "yolo-cage: direct API access is not permitted. Use specific gh commands instead.",
    "extension": "yolo-cage: managing extensions is not permitted.",
    "alias": "yolo-cage: managing aliases is not permitted.",
}


def get_gh_subcommand(args: list[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Extract the main command and subcommand from gh args.

    Returns (main_command, subcommand) tuple.
    For 'gh issue create', returns ('issue', 'create').
    For 'gh status', returns ('status', None).
    """
    main_cmd = None
    sub_cmd = None

    for arg in args:
        if arg.startswith("-"):
            continue
        if main_cmd is None:
            main_cmd = arg
        else:
            sub_cmd = arg
            break

    return main_cmd, sub_cmd


def classify_gh(args: list[str]) -> tuple[GhCommandCategory, Optional[str]]:
    """
    Classify a gh command.

    Returns (category, deny_message). deny_message is only set for BLOCKED.
    """
    main_cmd, sub_cmd = get_gh_subcommand(args)

    if main_cmd is None:
        return GhCommandCategory.UNKNOWN, None

    # Check if entirely blocked
    if main_cmd in FULLY_BLOCKED_COMMANDS:
        return GhCommandCategory.BLOCKED, FULLY_BLOCKED_COMMANDS[main_cmd]

    # Check if subcommand is specifically blocked
    if main_cmd in BLOCKED_COMMANDS:
        blocked_subs = BLOCKED_COMMANDS[main_cmd]
        if sub_cmd in blocked_subs:
            return GhCommandCategory.BLOCKED, blocked_subs[sub_cmd]

    # Check if command is allowed
    if main_cmd in ALLOWED_COMMANDS:
        allowed_subs = ALLOWED_COMMANDS[main_cmd]
        if allowed_subs is None:
            # All subcommands allowed
            return GhCommandCategory.ALLOWED, None
        if sub_cmd in allowed_subs:
            return GhCommandCategory.ALLOWED, None
        # Main command known but subcommand not in allowed list
        return GhCommandCategory.UNKNOWN, None

    # Unknown command
    return GhCommandCategory.UNKNOWN, None
