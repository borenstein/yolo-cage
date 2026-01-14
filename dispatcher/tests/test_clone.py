"""Tests for clone operations."""

from pathlib import Path
from unittest.mock import patch

import pytest

from dispatcher.clone import clone_and_checkout, CloneError
from dispatcher.models import GitResult


class TestCloneAndCheckout:
    """Tests for clone_and_checkout function."""

    def test_clone_and_checkout_existing_branch(self, tmp_path):
        """Successfully clone and checkout existing branch."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()

        def mock_execute_with_auth(args, cwd):
            if args[0] == "clone":
                (workspace / ".git").mkdir()
                return GitResult(0, "Cloning...", "")
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "ls-remote":
                return GitResult(0, "abc123\trefs/heads/test-branch", "")
            if args[0] == "checkout":
                return GitResult(0, "", "")
            return GitResult(0, "", "")

        with patch("dispatcher.clone.REPO_URL", "https://github.com/test/repo.git"):
            with patch("dispatcher.clone.execute_with_auth", mock_execute_with_auth):
                with patch("dispatcher.clone.execute", mock_execute):
                    result = clone_and_checkout(workspace, "test-branch")

        assert result["status"] == "success"
        assert result["action"] == "checked_out"
        assert result["cloned"] is True

    def test_clone_and_create_new_branch(self, tmp_path):
        """Successfully clone and create new branch when it doesn't exist."""
        workspace = tmp_path / "feature-new"
        workspace.mkdir()

        def mock_execute_with_auth(args, cwd):
            if args[0] == "clone":
                (workspace / ".git").mkdir()
                return GitResult(0, "Cloning...", "")
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "ls-remote":
                return GitResult(0, "", "")  # Branch doesn't exist
            if args[0] == "checkout" and "-b" in args:
                return GitResult(0, "", "")
            return GitResult(0, "", "")

        with patch("dispatcher.clone.REPO_URL", "https://github.com/test/repo.git"):
            with patch("dispatcher.clone.execute_with_auth", mock_execute_with_auth):
                with patch("dispatcher.clone.execute", mock_execute):
                    result = clone_and_checkout(workspace, "feature-new")

        assert result["status"] == "success"
        assert result["action"] == "created"
        assert result["cloned"] is True

    def test_clone_failure_raises_error(self, tmp_path):
        """Clone failure raises CloneError."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()

        def mock_execute_with_auth(args, cwd):
            return GitResult(128, "", "fatal: repository not found")

        with patch("dispatcher.clone.REPO_URL", "https://github.com/test/repo.git"):
            with patch("dispatcher.clone.execute_with_auth", mock_execute_with_auth):
                with pytest.raises(CloneError) as exc:
                    clone_and_checkout(workspace, "test-branch")
                assert "Failed to clone" in str(exc.value)

    def test_checkout_failure_raises_error(self, tmp_path):
        """Checkout failure after successful clone raises CloneError."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()

        def mock_execute_with_auth(args, cwd):
            if args[0] == "clone":
                (workspace / ".git").mkdir()
                return GitResult(0, "Cloning...", "")
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "ls-remote":
                return GitResult(0, "abc123\trefs/heads/test-branch", "")
            if args[0] == "checkout":
                return GitResult(1, "", "error: pathspec 'test-branch' did not match")
            return GitResult(0, "", "")

        with patch("dispatcher.clone.REPO_URL", "https://github.com/test/repo.git"):
            with patch("dispatcher.clone.execute_with_auth", mock_execute_with_auth):
                with patch("dispatcher.clone.execute", mock_execute):
                    with pytest.raises(CloneError) as exc:
                        clone_and_checkout(workspace, "test-branch")
                    assert "Failed to checkout" in str(exc.value)
