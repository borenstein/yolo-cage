"""Tests for pre-push hook execution."""

import pytest
from unittest.mock import patch, MagicMock

from dispatcher.hooks import HookResult, _run_single_hook, run_pre_push_hooks


class TestRunSingleHook:
    """Tests for single hook execution."""

    @patch("dispatcher.hooks.subprocess.run")
    def test_successful_hook(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Hook passed\n",
            stderr="",
        )
        result = _run_single_hook("echo test", "/workspace")

        assert result.success is True
        assert "Hook passed" in result.output
        assert result.hook_cmd == "echo test"

    @patch("dispatcher.hooks.subprocess.run")
    def test_failed_hook(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Hook failed\n",
        )
        result = _run_single_hook("false", "/workspace")

        assert result.success is False
        assert "Hook failed" in result.output

    @patch("dispatcher.hooks.subprocess.run")
    def test_hook_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="slow", timeout=120)

        result = _run_single_hook("sleep 1000", "/workspace")

        assert result.success is False
        assert "timed out" in result.output

    @patch("dispatcher.hooks.subprocess.run")
    def test_hook_exception(self, mock_run):
        mock_run.side_effect = Exception("Unexpected error")

        result = _run_single_hook("broken", "/workspace")

        assert result.success is False
        assert "failed" in result.output.lower()

    @patch("dispatcher.hooks.subprocess.run")
    def test_hook_runs_in_correct_directory(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_single_hook("pwd", "/my/workspace")

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == "/my/workspace"

    @patch("dispatcher.hooks.subprocess.run")
    def test_hook_runs_with_shell(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_single_hook("echo $HOME && ls", "/workspace")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["shell"] is True


class TestRunPrePushHooks:
    """Tests for running all pre-push hooks."""

    @patch("dispatcher.hooks.PRE_PUSH_HOOKS", [])
    def test_no_hooks_configured(self):
        success, output = run_pre_push_hooks("/workspace")
        assert success is True
        assert output == ""

    @patch("dispatcher.hooks.PRE_PUSH_HOOKS", ["echo hook1"])
    @patch("dispatcher.hooks._run_single_hook")
    def test_single_hook_success(self, mock_run):
        mock_run.return_value = HookResult(
            success=True,
            output="hook1 output",
            hook_cmd="echo hook1",
        )

        success, output = run_pre_push_hooks("/workspace")

        assert success is True
        assert "hook1 output" in output

    @patch("dispatcher.hooks.PRE_PUSH_HOOKS", ["echo hook1", "echo hook2"])
    @patch("dispatcher.hooks._run_single_hook")
    def test_multiple_hooks_all_success(self, mock_run):
        mock_run.side_effect = [
            HookResult(success=True, output="hook1 ok", hook_cmd="echo hook1"),
            HookResult(success=True, output="hook2 ok", hook_cmd="echo hook2"),
        ]

        success, output = run_pre_push_hooks("/workspace")

        assert success is True
        assert "hook1 ok" in output
        assert "hook2 ok" in output

    @patch("dispatcher.hooks.PRE_PUSH_HOOKS", ["echo hook1", "false", "echo hook3"])
    @patch("dispatcher.hooks._run_single_hook")
    def test_stops_on_first_failure(self, mock_run):
        mock_run.side_effect = [
            HookResult(success=True, output="hook1 ok", hook_cmd="echo hook1"),
            HookResult(success=False, output="hook2 failed", hook_cmd="false"),
            HookResult(success=True, output="hook3 ok", hook_cmd="echo hook3"),
        ]

        success, output = run_pre_push_hooks("/workspace")

        assert success is False
        assert "hook1 ok" in output
        assert "hook2 failed" in output
        # hook3 should not be in output (not run)
        assert "hook3 ok" not in output
        # Should have only called 2 hooks
        assert mock_run.call_count == 2

    @patch("dispatcher.hooks.PRE_PUSH_HOOKS", ["secret-scanner"])
    @patch("dispatcher.hooks._run_single_hook")
    def test_first_hook_fails(self, mock_run):
        mock_run.return_value = HookResult(
            success=False,
            output="Found secrets!",
            hook_cmd="secret-scanner",
        )

        success, output = run_pre_push_hooks("/workspace")

        assert success is False
        assert "Found secrets" in output
