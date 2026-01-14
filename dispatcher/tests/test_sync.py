"""Tests for workspace sync operations."""

from pathlib import Path
from unittest.mock import patch

import pytest

from dispatcher.sync import update_workspace, SyncError
from dispatcher.models import GitResult


class TestUpdateWorkspace:
    """Tests for updating existing workspace."""

    def test_already_on_correct_branch(self, tmp_path):
        """Returns early if already on the correct branch."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()
        (workspace / ".git").mkdir()

        def mock_execute_with_auth(args, cwd):
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "rev-parse":
                return GitResult(0, "test-branch\n", "")
            return GitResult(0, "", "")

        with patch("dispatcher.sync.execute_with_auth", mock_execute_with_auth):
            with patch("dispatcher.sync.execute", mock_execute):
                result = update_workspace(workspace, "test-branch")

        assert result["status"] == "success"
        assert result["action"] == "already_on_branch"
        assert result["cloned"] is False

    def test_switch_to_existing_local_branch(self, tmp_path):
        """Switch to a branch that exists locally."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()
        (workspace / ".git").mkdir()

        checkout_called = []

        def mock_execute_with_auth(args, cwd):
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "rev-parse":
                return GitResult(0, "main\n", "")  # On different branch
            if args[0] == "show-ref":
                return GitResult(0, "", "")  # Branch exists locally
            if args[0] == "checkout":
                checkout_called.append(args)
                return GitResult(0, "", "")
            return GitResult(0, "", "")

        with patch("dispatcher.sync.execute_with_auth", mock_execute_with_auth):
            with patch("dispatcher.sync.execute", mock_execute):
                result = update_workspace(workspace, "test-branch")

        assert result["status"] == "success"
        assert result["action"] == "switched_branch"
        assert len(checkout_called) == 1
        assert checkout_called[0] == ["checkout", "test-branch"]

    def test_switch_to_remote_branch(self, tmp_path):
        """Switch to a branch that exists on remote but not locally."""
        workspace = tmp_path / "feature"
        workspace.mkdir()
        (workspace / ".git").mkdir()

        checkout_called = []

        def mock_execute_with_auth(args, cwd):
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "rev-parse":
                return GitResult(0, "main\n", "")
            if args[0] == "show-ref":
                return GitResult(1, "", "")  # Branch doesn't exist locally
            if args[0] == "ls-remote":
                return GitResult(0, "abc123\trefs/heads/feature", "")  # Exists on remote
            if args[0] == "checkout":
                checkout_called.append(args)
                return GitResult(0, "", "")
            return GitResult(0, "", "")

        with patch("dispatcher.sync.execute_with_auth", mock_execute_with_auth):
            with patch("dispatcher.sync.execute", mock_execute):
                result = update_workspace(workspace, "feature")

        assert result["status"] == "success"
        assert result["action"] == "switched_branch"
        assert checkout_called[0] == ["checkout", "-b", "feature", "origin/feature"]

    def test_create_new_branch(self, tmp_path):
        """Create new branch when it doesn't exist locally or remotely."""
        workspace = tmp_path / "new-feature"
        workspace.mkdir()
        (workspace / ".git").mkdir()

        checkout_called = []

        def mock_execute_with_auth(args, cwd):
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "rev-parse":
                return GitResult(0, "main\n", "")
            if args[0] == "show-ref":
                return GitResult(1, "", "")  # Not local
            if args[0] == "ls-remote":
                return GitResult(0, "", "")  # Not remote
            if args[0] == "checkout":
                checkout_called.append(args)
                return GitResult(0, "", "")
            return GitResult(0, "", "")

        with patch("dispatcher.sync.execute_with_auth", mock_execute_with_auth):
            with patch("dispatcher.sync.execute", mock_execute):
                result = update_workspace(workspace, "new-feature")

        assert result["status"] == "success"
        assert checkout_called[0] == ["checkout", "-b", "new-feature"]

    def test_checkout_failure_raises_error(self, tmp_path):
        """Checkout failure raises SyncError."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()
        (workspace / ".git").mkdir()

        def mock_execute_with_auth(args, cwd):
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "rev-parse":
                return GitResult(0, "main\n", "")
            if args[0] == "show-ref":
                return GitResult(0, "", "")  # Branch exists locally
            if args[0] == "checkout":
                return GitResult(1, "", "error: cannot checkout")
            return GitResult(0, "", "")

        with patch("dispatcher.sync.execute_with_auth", mock_execute_with_auth):
            with patch("dispatcher.sync.execute", mock_execute):
                with pytest.raises(SyncError) as exc:
                    update_workspace(workspace, "test-branch")
                assert "Failed to checkout" in str(exc.value)
