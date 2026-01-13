"""Tests for the /gh endpoint in the FastAPI app."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from dispatcher.app import app
from dispatcher.gh_commands import GhCommandCategory
from dispatcher.models import GhResult


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def registered_pod():
    """Register a test pod and clean up after."""
    from dispatcher import registry
    test_ip = "testclient"
    registry.register(test_ip, "feature-branch")
    yield test_ip
    registry.deregister(test_ip)


class TestGhEndpointUnregistered:
    """Tests for unregistered pods."""

    def test_unregistered_pod_denied(self, client):
        """Unregistered pods should be denied."""
        # Clear any existing registration
        from dispatcher import registry
        registry.deregister("testclient")

        response = client.post(
            "/gh",
            json={"args": ["status"], "cwd": "/workspace"},
        )
        assert response.status_code == 403
        assert "not registered" in response.text


class TestGhEndpointAllowed:
    """Tests for allowed gh commands."""

    @patch("dispatcher.app.gh_execute")
    def test_allowed_command_executes(self, mock_execute, client, registered_pod):
        """Allowed commands should be executed."""
        mock_execute.return_value = GhResult(
            exit_code=0,
            stdout="issue list output",
            stderr="",
        )
        response = client.post(
            "/gh",
            json={"args": ["issue", "list"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "issue list output" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "0"
        mock_execute.assert_called_once_with(["issue", "list"], "/workspace")

    @patch("dispatcher.app.gh_execute")
    def test_pr_create_allowed(self, mock_execute, client, registered_pod):
        """PR create should be allowed."""
        mock_execute.return_value = GhResult(
            exit_code=0,
            stdout="https://github.com/owner/repo/pull/123",
            stderr="",
        )
        response = client.post(
            "/gh",
            json={"args": ["pr", "create", "--title", "Test PR"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "pull/123" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "0"

    @patch("dispatcher.app.gh_execute")
    def test_pr_view_allowed(self, mock_execute, client, registered_pod):
        """PR view should be allowed."""
        mock_execute.return_value = GhResult(
            exit_code=0,
            stdout="PR details here",
            stderr="",
        )
        response = client.post(
            "/gh",
            json={"args": ["pr", "view", "123"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "0"


class TestGhEndpointBlocked:
    """Tests for blocked gh commands."""

    def test_pr_merge_blocked(self, client, registered_pod):
        """PR merge should be blocked."""
        response = client.post(
            "/gh",
            json={"args": ["pr", "merge", "123"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "merging PRs is not permitted" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"

    def test_repo_delete_blocked(self, client, registered_pod):
        """Repo delete should be blocked."""
        response = client.post(
            "/gh",
            json={"args": ["repo", "delete", "owner/repo"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "deleting repositories is not permitted" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"

    def test_api_blocked(self, client, registered_pod):
        """Direct API access should be blocked."""
        response = client.post(
            "/gh",
            json={"args": ["api", "/repos/owner/repo"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "direct API access is not permitted" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"

    def test_auth_login_blocked(self, client, registered_pod):
        """Auth operations should be blocked."""
        response = client.post(
            "/gh",
            json={"args": ["auth", "login"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "authentication is managed by the sandbox" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"

    def test_secret_set_blocked(self, client, registered_pod):
        """Secret operations should be blocked."""
        response = client.post(
            "/gh",
            json={"args": ["secret", "set", "MY_SECRET"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "managing secrets is not permitted" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"


class TestGhEndpointUnknown:
    """Tests for unknown gh commands."""

    def test_unknown_command_blocked(self, client, registered_pod):
        """Unknown commands should be blocked."""
        response = client.post(
            "/gh",
            json={"args": ["unknown-command"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "unrecognized or disallowed gh operation" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"

    def test_empty_args_blocked(self, client, registered_pod):
        """Empty args should be blocked."""
        response = client.post(
            "/gh",
            json={"args": [], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "unrecognized or disallowed gh operation" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"


class TestGhEndpointExecutionErrors:
    """Tests for execution error handling."""

    @patch("dispatcher.app.gh_execute")
    def test_command_returns_nonzero_exit(self, mock_execute, client, registered_pod):
        """Non-zero exit codes should be passed through."""
        mock_execute.return_value = GhResult(
            exit_code=1,
            stdout="",
            stderr="gh: Not Found",
        )
        response = client.post(
            "/gh",
            json={"args": ["repo", "view", "nonexistent/repo"], "cwd": "/workspace"},
        )
        assert response.status_code == 200
        assert "Not Found" in response.text
        assert response.headers.get("X-Yolo-Cage-Exit-Code") == "1"
