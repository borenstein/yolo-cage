"""
Policy enforcement for the egress proxy.

Loads blocklists from environment variables (ConfigMap).
This is defense-in-depth; primary protection is the git dispatcher.
"""

import json
import os
import re
from typing import Optional

# Default blocked domains (used if BLOCKED_DOMAINS env not set)
_DEFAULT_BLOCKED_DOMAINS = [
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
]

# Default GitHub API blocked patterns (used if GITHUB_API_BLOCKED env not set)
_DEFAULT_GITHUB_API_BLOCKED = [
    ("PUT", r"/repos/[^/]+/[^/]+/pulls/\d+/merge"),
    ("DELETE", r"/repos/.*"),
    ("DELETE", r"/orgs/.*"),
    ("DELETE", r"/user/.*"),
    ("GET", r"/repos/[^/]+/[^/]+/actions/secrets.*"),
    ("GET", r"/orgs/[^/]+/actions/secrets.*"),
    ("PATCH", r"/repos/[^/]+/[^/]+$"),
    ("PUT", r"/repos/[^/]+/[^/]+/collaborators.*"),
    ("POST", r"/repos/[^/]+/[^/]+/hooks"),
    ("PATCH", r"/repos/[^/]+/[^/]+/hooks/\d+"),
    ("PUT", r"/repos/[^/]+/[^/]+/branches/[^/]+/protection"),
    ("DELETE", r"/repos/[^/]+/[^/]+/branches/[^/]+/protection"),
]


def _load_blocked_domains() -> frozenset[str]:
    """Load blocked domains from environment or use defaults."""
    env_value = os.environ.get("BLOCKED_DOMAINS")
    if env_value:
        try:
            domains = json.loads(env_value)
            return frozenset(domains)
        except json.JSONDecodeError:
            pass
    return frozenset(_DEFAULT_BLOCKED_DOMAINS)


def _load_github_api_blocked() -> list[tuple[str, str]]:
    """Load GitHub API blocked patterns from environment or use defaults."""
    env_value = os.environ.get("GITHUB_API_BLOCKED")
    if env_value:
        try:
            patterns = json.loads(env_value)
            return [(method, pattern) for method, pattern in patterns]
        except json.JSONDecodeError:
            pass
    return _DEFAULT_GITHUB_API_BLOCKED


# Load configuration at module import time
BLOCKED_DOMAINS = _load_blocked_domains()
GITHUB_API_BLOCKED_PATTERNS = _load_github_api_blocked()


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
