"""Dispatcher client - HTTP client for dispatcher REST API."""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from ..errors import DispatcherError
from ..domain.branch import Branch
from ..domain.sandbox import Sandbox, SandboxStatus
from . import kubernetes


class DispatcherClient:
    """HTTP client for communicating with the git dispatcher service."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize dispatcher client.

        Args:
            base_url: Base URL of dispatcher (default: auto-discover from service)
        """
        if base_url is None:
            cluster_ip = kubernetes.get_service_cluster_ip("git-dispatcher")
            base_url = f"http://{cluster_ip}:8080"
        self.base_url = base_url.rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to dispatcher.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API path
            data: Request body data (for POST)

        Returns:
            Response JSON as dict

        Raises:
            DispatcherError: If request fails
        """
        url = f"{self.base_url}{path}"

        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")

        request_body = None
        if data is not None:
            request_body = json.dumps(data).encode("utf-8")

        try:
            with urllib.request.urlopen(req, data=request_body, timeout=30) as resp:
                response_data = resp.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get("detail", error_body)
            except json.JSONDecodeError:
                error_msg = error_body or str(e)
            raise DispatcherError(f"Dispatcher error ({e.code}): {error_msg}")
        except urllib.error.URLError as e:
            raise DispatcherError(f"Failed to connect to dispatcher: {e.reason}")
        except Exception as e:
            raise DispatcherError(f"Unexpected error communicating with dispatcher: {e}")

    def create_sandbox(self, branch: Branch) -> Dict[str, Any]:
        """Create a sandbox for a branch.

        Args:
            branch: Branch to create sandbox for

        Returns:
            Response from dispatcher with status/message

        Raises:
            DispatcherError: If creation fails
        """
        return self._request("POST", "/pods", data={"branch": branch.name})

    def list_sandboxes(self) -> List[Sandbox]:
        """List all sandboxes.

        Returns:
            List of Sandbox instances

        Raises:
            DispatcherError: If listing fails
        """
        response = self._request("GET", "/pods")
        pods_data = response.get("pods", [])

        sandboxes = []
        for pod_data in pods_data:
            branch = Branch(name=pod_data["branch"])
            status = SandboxStatus.from_pod_phase(pod_data.get("status", "Unknown"))
            sandboxes.append(Sandbox(branch=branch, status=status))

        return sandboxes

    def delete_sandbox(self, branch: Branch, clean: bool = False) -> Dict[str, Any]:
        """Delete a sandbox.

        Args:
            branch: Branch whose sandbox to delete
            clean: Whether to also delete workspace files

        Returns:
            Response from dispatcher

        Raises:
            DispatcherError: If deletion fails
        """
        path = f"/pods/{branch.name}"
        if clean:
            path += "?clean=true"
        return self._request("DELETE", path)
