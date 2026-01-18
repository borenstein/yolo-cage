"""Pod lifecycle management using Kubernetes client."""

import logging
import os
import re
import shutil
from pathlib import Path
from string import Template
from typing import Optional

import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .models import PodInfo, PodCreateResponse

logger = logging.getLogger(__name__)

NAMESPACE = "yolo-cage"
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/workspaces")
PROXY_BYPASS = os.environ.get("PROXY_BYPASS", ".anthropic.com,.claude.com")

# Pod template bundled into image at build time
TEMPLATE_PATH = Path("/app/pod-template.yaml")


def _init_k8s_client() -> client.CoreV1Api:
    """Initialize Kubernetes client."""
    config.load_incluster_config()
    return client.CoreV1Api()


def _sanitize_branch(branch: str) -> str:
    """Sanitize branch name for pod name."""
    return re.sub(r'[/_]', '-', branch.lower())


def _pod_name(branch: str) -> str:
    return f"yolo-cage-{_sanitize_branch(branch)}"


def _load_pod_template(branch: str) -> dict:
    """Load pod template and substitute variables."""
    template_text = TEMPLATE_PATH.read_text()

    # Substitute variables
    substituted = template_text.replace("${BRANCH}", branch)
    substituted = substituted.replace("${PROXY_BYPASS}", PROXY_BYPASS)

    return yaml.safe_load(substituted)


def create_pod(branch: str) -> PodCreateResponse:
    """Create a pod for the given branch."""
    v1 = _init_k8s_client()
    name = _pod_name(branch)

    # Check if already exists
    try:
        existing = v1.read_namespaced_pod(name=name, namespace=NAMESPACE)
        return PodCreateResponse(
            name=name,
            branch=branch,
            status=existing.status.phase,
            message=f"Pod already exists. Use 'yolo-cage attach {branch}' to connect."
        )
    except ApiException as e:
        if e.status != 404:
            raise

    # Load template and create pod
    manifest = _load_pod_template(branch)
    logger.info(f"Creating pod {name} for branch {branch}")

    v1.create_namespaced_pod(namespace=NAMESPACE, body=manifest)
    return PodCreateResponse(
        name=name,
        branch=branch,
        status="Pending",
        message="Pod created. Waiting for it to become ready..."
    )


def list_pods() -> list[PodInfo]:
    """List all yolo-cage pods."""
    v1 = _init_k8s_client()

    pods = v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector="app=yolo-cage"
    )

    return [
        PodInfo(
            name=pod.metadata.name,
            branch=pod.metadata.labels.get("yolo-cage/branch", "unknown"),
            status=pod.status.phase,
            ip=pod.status.pod_ip,
            created_at=pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
        )
        for pod in pods.items
    ]


def get_pod(branch: str) -> Optional[PodInfo]:
    """Get pod by branch name."""
    v1 = _init_k8s_client()
    name = _pod_name(branch)

    try:
        pod = v1.read_namespaced_pod(name=name, namespace=NAMESPACE)
        return PodInfo(
            name=pod.metadata.name,
            branch=pod.metadata.labels.get("yolo-cage/branch", branch),
            status=pod.status.phase,
            ip=pod.status.pod_ip,
            created_at=pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
        )
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def delete_pod(branch: str, clean_workspace: bool = False) -> bool:
    """Delete pod. Returns True if deleted, False if not found."""
    v1 = _init_k8s_client()
    name = _pod_name(branch)

    try:
        v1.delete_namespaced_pod(name=name, namespace=NAMESPACE)
        logger.info(f"Deleted pod {name}")

        if clean_workspace:
            workspace_path = Path(WORKSPACE_ROOT) / branch
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
                logger.info(f"Deleted workspace {workspace_path}")

        return True
    except ApiException as e:
        if e.status == 404:
            return False
        raise
