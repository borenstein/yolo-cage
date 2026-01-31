"""Kubernetes utilities - kubectl wrapper operations."""

import json
import subprocess
from typing import List, Optional

from ..common.errors import KubernetesError


NAMESPACE = "yolo-cage"


def get_service_cluster_ip(service_name: str) -> str:
    """Get the ClusterIP of a service.

    Args:
        service_name: Name of the service

    Returns:
        ClusterIP address

    Raises:
        KubernetesError: If service not found or kubectl fails
    """
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "svc",
                "-n",
                NAMESPACE,
                service_name,
                "-o",
                "jsonpath={.spec.clusterIP}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        cluster_ip = result.stdout.strip()
        if not cluster_ip:
            raise KubernetesError(f"Service {service_name} has no ClusterIP")
        return cluster_ip
    except subprocess.CalledProcessError as e:
        raise KubernetesError(f"Failed to get service {service_name}: {e.stderr}")


def wait_for_pod_ready(pod_name: str, timeout_seconds: int = 120) -> None:
    """Wait for a pod to become Ready.

    Args:
        pod_name: Name of the pod
        timeout_seconds: Maximum time to wait

    Raises:
        KubernetesError: If pod doesn't become ready within timeout
    """
    try:
        subprocess.run(
            [
                "kubectl",
                "wait",
                "--for=condition=Ready",
                f"pod/{pod_name}",
                "-n",
                NAMESPACE,
                f"--timeout={timeout_seconds}s",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise KubernetesError(f"Pod {pod_name} did not become ready: {e.stderr}")


def exec_in_pod(pod_name: str, command: List[str], interactive: bool = True) -> int:
    """Execute a command in a pod.

    Args:
        pod_name: Name of the pod
        command: Command and arguments to execute
        interactive: Whether to allocate TTY and STDIN

    Returns:
        Exit code from kubectl exec

    Raises:
        KubernetesError: If kubectl exec fails
    """
    kubectl_cmd = ["kubectl", "exec", "-n", NAMESPACE]

    if interactive:
        kubectl_cmd.extend(["-it"])

    kubectl_cmd.append(pod_name)
    kubectl_cmd.append("--")
    kubectl_cmd.extend(command)

    try:
        return subprocess.call(kubectl_cmd)
    except Exception as e:
        raise KubernetesError(f"Failed to exec in pod {pod_name}: {e}")


def tail_pod_logs(pod_name: str) -> int:
    """Tail logs from a pod.

    Args:
        pod_name: Name of the pod

    Returns:
        Exit code from kubectl logs

    Raises:
        KubernetesError: If kubectl logs fails
    """
    try:
        return subprocess.call(
            ["kubectl", "logs", "-n", NAMESPACE, pod_name, "-f"]
        )
    except Exception as e:
        raise KubernetesError(f"Failed to tail logs for pod {pod_name}: {e}")


def pod_exists(pod_name: str) -> bool:
    """Check if a pod exists.

    Args:
        pod_name: Name of the pod

    Returns:
        True if pod exists, False otherwise
    """
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "pod",
                "-n",
                NAMESPACE,
                pod_name,
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False
