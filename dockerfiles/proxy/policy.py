"""
Policy enforcement for the egress proxy.

Contains domain blocklists and GitHub API restrictions.
This is defense-in-depth; primary protection is the git dispatcher.
"""

import re
from typing import Optional

# Blocklist for known exfiltration sites
BLOCKED_DOMAINS = frozenset({
    "pastebin.com",
    "paste.ee",
    "hastebin.com",
    "dpaste.org",
    "file.io",
    "transfer.sh",
    "0x0.st",
    "ix.io",
    "sprunge.us",
    "termbin.com",
})

# GitHub API policy - dangerous endpoints that agents cannot access
GITHUB_API_BLOCKED_PATTERNS = [
    # Cannot merge PRs (agent proposes, human disposes)
    ("PUT", r"/repos/[^/]+/[^/]+/pulls/\d+/merge"),
    # Cannot delete anything
    ("DELETE", r"/repos/.*"),
    ("DELETE", r"/orgs/.*"),
    ("DELETE", r"/user/.*"),
    # Cannot read GitHub Actions secrets
    ("GET", r"/repos/[^/]+/[^/]+/actions/secrets.*"),
    ("GET", r"/orgs/[^/]+/actions/secrets.*"),
    # Cannot modify repository settings
    ("PATCH", r"/repos/[^/]+/[^/]+$"),
    ("PUT", r"/repos/[^/]+/[^/]+/collaborators.*"),
    # Cannot create/modify webhooks
    ("POST", r"/repos/[^/]+/[^/]+/hooks"),
    ("PATCH", r"/repos/[^/]+/[^/]+/hooks/\d+"),
    # Cannot modify branch protection
    ("PUT", r"/repos/[^/]+/[^/]+/branches/[^/]+/protection"),
    ("DELETE", r"/repos/[^/]+/[^/]+/branches/[^/]+/protection"),
]


def check_blocked_domain(host: str) -> Optional[str]:
    """
    Check if a host is on the domain blocklist.
    Returns the matched domain if blocked, None if allowed.
    """
    for blocked_domain in BLOCKED_DOMAINS:
        if host == blocked_domain or host.endswith(f".{blocked_domain}"):
            return blocked_domain
    return None


def check_github_api(host: str, method: str, path: str) -> Optional[str]:
    """
    Check if a GitHub API request is allowed.
    Returns blocking reason if blocked, None if allowed.
    """
    if host not in ("api.github.com", "github.com"):
        return None

    for blocked_method, pattern in GITHUB_API_BLOCKED_PATTERNS:
        if method == blocked_method and re.match(pattern, path):
            return f"github_api_blocked:{blocked_method} {pattern}"

    return None
