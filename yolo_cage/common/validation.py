"""Validation utilities - Configuration and input validation."""

import re
from typing import Optional, Tuple


def parse_github_repo(repo_url: str) -> Optional[Tuple[str, str]]:
    """Extract owner and repo name from a GitHub URL.

    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - git@github.com:owner/repo.git

    Args:
        repo_url: GitHub repository URL

    Returns:
        Tuple of (owner, repo) or None if not a valid GitHub URL
    """
    # HTTPS format
    match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if match:
        return match.group(1), match.group(2)

    # SSH format
    match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
    if match:
        return match.group(1), match.group(2)

    return None


def validate_branch_name(branch: str) -> bool:
    """Validate git branch name.

    Args:
        branch: Branch name to validate

    Returns:
        True if valid, False otherwise
    """
    if not branch:
        return False
    if branch.startswith("-"):
        return False
    # Could add more git ref validation here
    return True
