"""GitHub repository utilities."""

import json
import re
import urllib.error
import urllib.request


def parse_github_repo(repo_url: str) -> tuple[str, str] | None:
    """Extract owner and repo name from a GitHub URL.

    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - git@github.com:owner/repo.git

    Returns (owner, repo) or None if not a valid GitHub URL.
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


def validate_github_repo(repo_url: str, pat: str) -> tuple[bool, str]:
    """Check if a GitHub repository is accessible with the given PAT.

    Returns (success, message) tuple.
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
            return (
                False,
                f"Repository not found: {owner}/{repo}\n"
                "Check that the repository exists and your PAT has access to it.",
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
