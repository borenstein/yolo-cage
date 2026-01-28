"""GitHub repository utilities."""

import json
import re
import urllib.error
import urllib.request

HTTPS_PATTERN = re.compile(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")
SSH_PATTERN = re.compile(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$")


def parse_github_repo(repo_url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from GitHub URL, or None if invalid."""
    for pattern in (HTTPS_PATTERN, SSH_PATTERN):
        match = pattern.match(repo_url)
        if match:
            return match.group(1), match.group(2)
    return None


def _build_api_request(owner: str, repo: str, pat: str) -> urllib.request.Request:
    req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}")
    req.add_header("Authorization", f"token {pat}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "yolo-cage")
    return req


def _check_push_access(data: dict, owner: str, repo: str) -> tuple[bool, str]:
    if not data.get("permissions", {}).get("push"):
        return False, f"PAT lacks push access to {owner}/{repo}"
    return True, f"Repository {owner}/{repo} is accessible"


def _handle_http_error(e: urllib.error.HTTPError, owner: str, repo: str) -> tuple[bool, str]:
    messages = {
        404: f"Repository not found: {owner}/{repo}",
        401: "Invalid or expired GitHub PAT.",
        403: f"Access denied to {owner}/{repo}.",
    }
    return False, messages.get(e.code, f"GitHub API error: {e.code}")


def validate_github_repo(repo_url: str, pat: str) -> tuple[bool, str]:
    """Check if repository is accessible with PAT. Returns (success, message)."""
    parsed = parse_github_repo(repo_url)
    if not parsed:
        return False, f"Could not parse GitHub URL: {repo_url}"

    owner, repo = parsed
    req = _build_api_request(owner, repo, pat)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _check_push_access(json.loads(resp.read().decode()), owner, repo)
    except urllib.error.HTTPError as e:
        return _handle_http_error(e, owner, repo)
    except urllib.error.URLError as e:
        return False, f"Could not connect to GitHub: {e.reason}"
