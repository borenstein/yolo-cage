"""Tests for workspace bootstrap orchestration."""

from pathlib import Path
from unittest.mock import patch

import pytest

from dispatcher.bootstrap import bootstrap_workspace, BootstrapError


class TestBootstrapWorkspace:
    """Tests for the main bootstrap_workspace entry point."""

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
                with patch("dispatcher.bootstrap.clone_and_checkout") as mock_clone:
                    mock_clone.return_value = {"status": "success"}
                    bootstrap_workspace("test-branch")

        assert workspace.exists()

    def test_routes_to_clone_for_empty_workspace(self, tmp_path):
        """Empty workspace routes to clone_and_checkout."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()

        with patch("dispatcher.bootstrap.WORKSPACE_ROOT", str(tmp_path)):
            with patch("dispatcher.bootstrap.REPO_URL", "https://github.com/test/repo.git"):
                with patch("dispatcher.bootstrap.clone_and_checkout") as mock_clone:
                    mock_clone.return_value = {"status": "success", "action": "cloned"}
                    result = bootstrap_workspace("test-branch")

        mock_clone.assert_called_once_with(workspace, "test-branch")
        assert result["action"] == "cloned"

    def test_routes_to_update_for_existing_git(self, tmp_path):
        """Workspace with .git routes to update_workspace."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()
        (workspace / ".git").mkdir()

        with patch("dispatcher.bootstrap.WORKSPACE_ROOT", str(tmp_path)):
            with patch("dispatcher.bootstrap.REPO_URL", "https://github.com/test/repo.git"):
                with patch("dispatcher.bootstrap.update_workspace") as mock_update:
                    mock_update.return_value = {"status": "success", "action": "updated"}
                    result = bootstrap_workspace("test-branch")

        mock_update.assert_called_once_with(workspace, "test-branch")
        assert result["action"] == "updated"

    def test_raises_error_for_files_without_git(self, tmp_path):
        """Workspace with files but no .git raises BootstrapError."""
        workspace = tmp_path / "test-branch"
        workspace.mkdir()
        (workspace / "some_file.txt").write_text("content")

        with patch("dispatcher.bootstrap.WORKSPACE_ROOT", str(tmp_path)):
            with patch("dispatcher.bootstrap.REPO_URL", "https://github.com/test/repo.git"):
                with pytest.raises(BootstrapError) as exc:
                    bootstrap_workspace("test-branch")
                assert "has files but no .git directory" in str(exc.value)
                assert "corrupted or manually modified" in str(exc.value)
