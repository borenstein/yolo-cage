"""GitHub API utilities - Repository validation and access checking."""

import json
import urllib.request
import urllib.error
from typing import Tuple

from .errors import GitHubAPIError
from .validation import parse_github_repo


def validate_github_repo(repo_url: str, pat: str) -> Tuple[bool, str]:
    """Check if a GitHub repository is accessible with the given PAT.

    Args:
        repo_url: GitHub repository URL
        pat: GitHub Personal Access Token

    Returns:
        Tuple of (success: bool, message: str)

    Raises:
        GitHubAPIError: If validation encounters an error
    """
    parsed = parse_github_repo(repo_url)
    if not parsed:
        return False, f"Could not parse GitHub URL: {repo_url}"

    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    req = urllib.request.Request(api_url)
    req.add_header("Authorization", f"token {pat}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "yolo-cage")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            # Check if we have push access
            permissions = data.get("permissions", {})
            if not permissions.get("push"):
                return False, f"PAT does not have push access to {owner}/{repo}"
            return True, f"Repository {owner}/{repo} is accessible"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, (
                f"Repository not found: {owner}/{repo}\n"
                f"Check that the repository exists and your PAT has access to it."
            )
        elif e.code == 401:
            return False, "Invalid GitHub PAT or PAT has expired."
        elif e.code == 403:
            return False, f"Access denied to {owner}/{repo}. Check your PAT permissions."
        else:
            return False, f"GitHub API error: {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Could not connect to GitHub: {e.reason}"
    except Exception as e:
        return False, f"Unexpected error validating repository: {e}"
