"""Tests for GitHub module."""

import pytest
from yolo_cage.github import parse_github_repo


class TestParseGithubRepo:
    """Tests for parse_github_repo function."""

    def test_https_url(self):
        """Parse HTTPS URL without .git suffix."""
        result = parse_github_repo("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_https_url_with_git_suffix(self):
        """Parse HTTPS URL with .git suffix."""
        result = parse_github_repo("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_https_url_with_trailing_slash(self):
        """Parse HTTPS URL with trailing slash."""
        result = parse_github_repo("https://github.com/owner/repo/")
        assert result == ("owner", "repo")

    def test_ssh_url(self):
        """Parse SSH URL."""
        result = parse_github_repo("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")

    def test_ssh_url_without_git_suffix(self):
        """Parse SSH URL without .git suffix."""
        result = parse_github_repo("git@github.com:owner/repo")
        assert result == ("owner", "repo")

    def test_invalid_url_returns_none(self):
        """Invalid URLs return None."""
        assert parse_github_repo("not-a-url") is None
        assert parse_github_repo("https://gitlab.com/owner/repo") is None
        assert parse_github_repo("") is None

    def test_repo_with_dashes(self):
        """Parse repo names with dashes."""
        result = parse_github_repo("https://github.com/my-org/my-repo")
        assert result == ("my-org", "my-repo")

    def test_repo_with_underscores(self):
        """Parse repo names with underscores."""
        result = parse_github_repo("https://github.com/my_org/my_repo")
        assert result == ("my_org", "my_repo")
