"""GitHub API utilities."""

import json
import re
import urllib.request
import urllib.error


def parse_repo_url(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from GitHub URL, or None if invalid."""
    patterns = [
        re.compile(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"),
        re.compile(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$"),
    ]
    for pattern in patterns:
        match = pattern.match(url)
        if match:
            return match.group(1), match.group(2)
    return None


def validate_repo_access(repo_url: str, pat: str) -> tuple[bool, str]:
    """Check if PAT has push access to repository.

    Returns (success, message) tuple.
    """
    parsed = parse_repo_url(repo_url)
    if not parsed:
        return False, f"Invalid GitHub URL: {repo_url}"

    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    req = urllib.request.Request(api_url)
    req.add_header("Authorization", f"token {pat}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "yolo-cage")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if not data.get("permissions", {}).get("push"):
                return False, f"PAT lacks push access to {owner}/{repo}"
            return True, f"Repository {owner}/{repo} is accessible"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, f"Repository not found: {owner}/{repo}"
        elif e.code == 401:
            return False, "Invalid or expired GitHub PAT"
        elif e.code == 403:
            return False, f"Access denied to {owner}/{repo}"
        return False, f"GitHub API error: {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Could not connect to GitHub: {e.reason}"
