"""Tests for workspace bootstrap."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from dispatcher.bootstrap import (
    bootstrap_workspace,
    BootstrapError,
    _clone_fresh_workspace,
    _update_existing_workspace,
)
from dispatcher.models import GitResult


class TestBootstrapWorkspace:
    """Tests for the main bootstrap_workspace function."""

    def test_no_repo_url_raises_error(self):
        """Bootstrap fails if REPO_URL is not configured."""
        with patch("dispatcher.bootstrap.REPO_URL", ""):
            with pytest.raises(BootstrapError) as exc:
                bootstrap_workspace("test-branch")
            assert "REPO_URL not configured" in str(exc.value)

    def test_creates_workspace_directory(self, tmp_path):
        """Bootstrap creates the workspace directory if it doesn't exist."""
        workspace = tmp_path / "workspaces" / "test-branch"

        with patch("dispatcher.bootstrap.WORKSPACE_ROOT", str(tmp_path / "workspaces")):
            with patch("dispatcher.bootstrap.REPO_URL", "https://github.com/test/repo.git"):
                with patch("dispatcher.bootstrap._clone_fresh_workspace") as mock_clone:
                    mock_clone.return_value = {"status": "success"}
                    bootstrap_workspace("test-branch")

        assert workspace.exists()


class TestCloneFreshWorkspace:
    """Tests for cloning into a fresh workspace."""

    def test_clone_success_existing_branch(self, tmp_path):
        """Successfully clone and checkout existing branch."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()

        def mock_execute_with_auth(args, cwd):
            if args[0] == "clone":
                # Simulate clone creating .git
                (workspace / ".git").mkdir()
                return GitResult(0, "Cloning...", "")
            return GitResult(0, "", "")

        def mock_execute(args, cwd):
            if args[0] == "ls-remote":
                return GitResult(0, "abc123\trefs/heads/test-branch", "")
            if args[0] == "checkout":
                return GitResult(0, "", "")
            return GitResult(0, "", "")

        with patch("dispatcher.bootstrap.REPO_URL", "https://github.com/test/repo.git"):
            with patch("dispatcher.bootstrap.execute_with_auth", mock_execute_with_auth):
                with patch("dispatcher.bootstrap.execute", mock_execute):
                    result = _clone_fresh_workspace(workspace, "test-branch")

        assert result["status"] == "success"
        assert result["action"] == "checked_out"
        assert result["cloned"] is True

    def test_clone_success_new_branch(self, tmp_path):
        """Successfully clone and create new branch."""
        workspace = tmp_path / "test-branch"
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

        with patch("dispatcher.bootstrap.REPO_URL", "https://github.com/test/repo.git"):
            with patch("dispatcher.bootstrap.execute_with_auth", mock_execute_with_auth):
                with patch("dispatcher.bootstrap.execute", mock_execute):
                    result = _clone_fresh_workspace(workspace, "feature-new")

        assert result["status"] == "success"
        assert result["action"] == "created"
        assert result["cloned"] is True

    def test_clone_failure(self, tmp_path):
        """Clone failure raises BootstrapError."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()

        def mock_execute_with_auth(args, cwd):
            return GitResult(128, "", "fatal: repository not found")

        with patch("dispatcher.bootstrap.REPO_URL", "https://github.com/test/repo.git"):
            with patch("dispatcher.bootstrap.execute_with_auth", mock_execute_with_auth):
                with pytest.raises(BootstrapError) as exc:
                    _clone_fresh_workspace(workspace, "test-branch")
                assert "Failed to clone" in str(exc.value)


class TestUpdateExistingWorkspace:
    """Tests for updating an existing workspace."""

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

        with patch("dispatcher.bootstrap.execute_with_auth", mock_execute_with_auth):
            with patch("dispatcher.bootstrap.execute", mock_execute):
                result = _update_existing_workspace(workspace, "test-branch")

        assert result["status"] == "success"
        assert result["action"] == "already_on_branch"
        assert result["cloned"] is False

    def test_switch_to_existing_local_branch(self, tmp_path):
        """Switch to a branch that exists locally."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()
        (workspace / ".git").mkdir()

        def mock_execute_with_auth(args, cwd):
            return GitResult(0, "", "")

        call_count = {"checkout": 0, "show-ref": 0}

        def mock_execute(args, cwd):
            if args[0] == "rev-parse":
                return GitResult(0, "main\n", "")  # On different branch
            if args[0] == "show-ref":
                call_count["show-ref"] += 1
                return GitResult(0, "", "")  # Branch exists locally
            if args[0] == "checkout":
                call_count["checkout"] += 1
                return GitResult(0, "", "")
            return GitResult(0, "", "")

        with patch("dispatcher.bootstrap.execute_with_auth", mock_execute_with_auth):
            with patch("dispatcher.bootstrap.execute", mock_execute):
                result = _update_existing_workspace(workspace, "test-branch")

        assert result["status"] == "success"
        assert result["action"] == "switched_branch"
        assert call_count["checkout"] == 1
