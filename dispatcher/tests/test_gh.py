"""Tests for GitHub CLI execution module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from dispatcher.gh import execute, _base_env, _rewrite_args_with_temp_files


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


class TestRewriteArgsWithTempFiles:
    """Tests for temp file creation from transmitted content."""

    def test_no_body_file_unchanged(self):
        """Args without --body-file should pass through unchanged."""
        args = ["issue", "create", "--title", "Test"]
        new_args, temp_files = _rewrite_args_with_temp_files(args, {}, None)
        assert new_args == args
        assert temp_files == []

    def test_body_file_with_content(self):
        """--body-file <path> with transmitted content creates temp file."""
        args = ["issue", "create", "--body-file", "/tmp/body.md"]
        files = {"/tmp/body.md": "Issue body content"}
        new_args, temp_files = _rewrite_args_with_temp_files(args, files, None)

        assert len(temp_files) == 1
        assert os.path.exists(temp_files[0])
        with open(temp_files[0]) as f:
            assert f.read() == "Issue body content"
        assert new_args[0:2] == ["issue", "create"]
        assert new_args[2] == "--body-file"
        assert new_args[3] == temp_files[0]

        # Cleanup
        for f in temp_files:
            os.unlink(f)

    def test_body_file_stdin(self):
        """--body-file - with stdin content creates temp file."""
        args = ["pr", "create", "--body-file", "-"]
        new_args, temp_files = _rewrite_args_with_temp_files(args, {}, "Stdin content")

        assert len(temp_files) == 1
        assert os.path.exists(temp_files[0])
        with open(temp_files[0]) as f:
            assert f.read() == "Stdin content"
        assert new_args[0:2] == ["pr", "create"]
        assert new_args[2] == "--body-file"
        assert new_args[3] == temp_files[0]

        # Cleanup
        for f in temp_files:
            os.unlink(f)

    def test_body_file_without_content_passes_through(self):
        """--body-file <path> without transmitted content passes through."""
        args = ["issue", "create", "--body-file", "/local/file.md"]
        new_args, temp_files = _rewrite_args_with_temp_files(args, {}, None)

        assert new_args == args
        assert temp_files == []

    def test_body_file_stdin_without_content_passes_through(self):
        """--body-file - without stdin content passes through."""
        args = ["issue", "create", "--body-file", "-"]
        new_args, temp_files = _rewrite_args_with_temp_files(args, {}, None)

        assert new_args == args
        assert temp_files == []

    def test_preserves_other_args(self):
        """Other arguments should be preserved."""
        args = ["issue", "create", "--title", "Test", "--body-file", "/tmp/body.md", "--assignee", "me"]
        files = {"/tmp/body.md": "content"}
        new_args, temp_files = _rewrite_args_with_temp_files(args, files, None)

        assert new_args[0:4] == ["issue", "create", "--title", "Test"]
        assert new_args[4] == "--body-file"
        # new_args[5] is the temp file
        assert new_args[6:] == ["--assignee", "me"]

        # Cleanup
        for f in temp_files:
            os.unlink(f)


class TestExecuteWithFiles:
    """Tests for execute() with file content transmission."""

    @patch("dispatcher.gh.subprocess.run")
    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_execute_with_file_content(self, mock_run):
        """Execute rewrites args and creates temp files."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/1",
            stderr="",
        )
        result = execute(
            ["issue", "create", "--body-file", "/tmp/body.md"],
            "/workspace",
            files={"/tmp/body.md": "Issue content"},
        )
        assert result.exit_code == 0
        # Verify gh was called with rewritten temp file path
        call_args = mock_run.call_args
        assert call_args[0][0][0:3] == ["gh", "issue", "create"]
        assert call_args[0][0][3] == "--body-file"
        # The temp file should have been created and cleaned up

    @patch("dispatcher.gh.subprocess.run")
    @patch("dispatcher.gh.GITHUB_PAT", "test-token")
    def test_execute_with_stdin_content(self, mock_run):
        """Execute rewrites --body-file - to temp file."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/owner/repo/pull/1",
            stderr="",
        )
        result = execute(
            ["pr", "create", "--body-file", "-"],
            "/workspace",
            stdin_content="PR body from stdin",
        )
        assert result.exit_code == 0
        call_args = mock_run.call_args
        assert call_args[0][0][0:3] == ["gh", "pr", "create"]
        assert call_args[0][0][3] == "--body-file"
        # Temp file path should be used, not "-"
        assert call_args[0][0][4] != "-"
