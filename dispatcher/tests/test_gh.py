"""Tests for GitHub CLI execution module."""

import pytest
from unittest.mock import patch, MagicMock

from dispatcher.gh import execute, _base_env


class TestBaseEnv:
    """Tests for environment setup."""

    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_sets_github_token_when_available(self):
        env = _base_env()
        assert env["GITHUB_TOKEN"] == "test-token"
        assert env["GH_TOKEN"] == "test-token"
        assert env["GH_PROMPT_DISABLED"] == "1"

    @patch("dispatcher.gh.GITHUB_PAT", None)
    def test_no_token_when_not_configured(self):
        env = _base_env()
        assert "GITHUB_TOKEN" not in env or env.get("GITHUB_TOKEN") is None
        assert env["GH_PROMPT_DISABLED"] == "1"


class TestExecute:
    """Tests for gh command execution."""

    @patch("dispatcher.gh.subprocess.run")
    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_successful_command(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )
        result = execute(["issue", "list"], "/workspace")
        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        mock_run.assert_called_once()
        # Verify gh was called with correct args
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gh", "issue", "list"]
        assert call_args[1]["cwd"] == "/workspace"

    @patch("dispatcher.gh.subprocess.run")
    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_command_with_error(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error message",
        )
        result = execute(["repo", "view", "nonexistent"], "/workspace")
        assert result.exit_code == 1
        assert result.stderr == "error message"

    @patch("dispatcher.gh.subprocess.run")
    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=300)
        result = execute(["issue", "list"], "/workspace")
        assert result.exit_code == 1
        assert "timed out" in result.stderr

    @patch("dispatcher.gh.subprocess.run")
    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_gh_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        result = execute(["status"], "/workspace")
        assert result.exit_code == 1
        assert "not installed" in result.stderr

    @patch("dispatcher.gh.subprocess.run")
    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_generic_exception(self, mock_run):
        mock_run.side_effect = Exception("something went wrong")
        result = execute(["status"], "/workspace")
        assert result.exit_code == 1
        assert "failed to execute gh" in result.stderr
