"""Pod lifecycle management using Kubernetes client."""

import logging
import os
import re
from typing import Optional

import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .models import PodInfo, PodCreateResponse

logger = logging.getLogger(__name__)

# Namespace from environment, default to yolo-cage
NAMESPACE = os.environ.get("YOLO_CAGE_NAMESPACE", "yolo-cage")

# Proxy bypass list for NO_PROXY env var
PROXY_BYPASS = os.environ.get("PROXY_BYPASS", "api.anthropic.com")


def _init_k8s_client() -> client.CoreV1Api:
    """Initialize Kubernetes client with in-cluster config."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        # Fall back to kubeconfig for local development
        config.load_kube_config()
    return client.CoreV1Api()


def _sanitize_branch(branch: str) -> str:
    """Sanitize branch name for use in pod name (lowercase, replace / and _ with -)."""
    return re.sub(r'[/_]', '-', branch.lower())


def _pod_name(branch: str) -> str:
    """Get pod name from branch."""
    return f"yolo-cage-{_sanitize_branch(branch)}"


def _build_pod_manifest(branch: str) -> dict:
    """Build pod manifest from template with variable substitution."""
    sanitized = _sanitize_branch(branch)

    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"yolo-cage-{sanitized}",
            "labels": {
                "app": "yolo-cage",
                "yolo-cage/branch": branch
            }
        },
        "spec": {
            "restartPolicy": "Never",
            "terminationGracePeriodSeconds": 5,
            "securityContext": {
                "runAsUser": 1000,
                "runAsGroup": 1000,
                "fsGroup": 1000
            },
            "initContainers": [
                {
                    "name": "setup-ca",
                    "image": "python:3.12-slim-bookworm",
                    "command": ["/bin/sh", "-c"],
                    "args": [
                        "cat /etc/ssl/certs/ca-certificates.crt /proxy-ca/mitmproxy-ca.pem > /ca-bundle/ca-certificates-combined.crt && chmod 644 /ca-bundle/ca-certificates-combined.crt"
                    ],
                    "volumeMounts": [
                        {"name": "proxy-ca", "mountPath": "/proxy-ca", "readOnly": True},
                        {"name": "ca-bundle", "mountPath": "/ca-bundle"}
                    ]
                },
                {
                    "name": "setup-claude-home",
                    "image": "python:3.12-slim-bookworm",
                    "command": ["/bin/sh", "-c"],
                    "args": ["""
mkdir -p /pvc/.claude
if [ ! -f /pvc/.claude.json ]; then
    echo '{}' > /pvc/.claude.json
fi
if [ ! -f /pvc/.claude/CLAUDE.md ]; then
    cat > /pvc/.claude/CLAUDE.md <<'CLAUDE_EOF'
# yolo-cage Environment

You are running inside yolo-cage, a sandboxed environment for autonomous development.
Claude Code is running in YOLO mode (--dangerously-skip-permissions), but the sandbox
enforces containment at the infrastructure level.

## Your Constraints

- **Branch isolation**: You can only commit/push to your assigned branch
- **Read-only elsewhere**: You can read any branch, but cannot modify others
- **No PR merging**: You may open PRs for human review, but cannot merge them
- **Git enforcement**: Git operations go through a dispatcher that enforces these rules

## Your Capabilities

- Full read access to the repository (all branches)
- Read/write access to GitHub issues and PR comments
- Can open pull requests on your branch
- Can install packages, run tests, do anything inside this container
- Full access to development tools (npm, pip, make, etc.)

## Workflow

1. Work in this workspace (your branch is set via $YOLO_CAGE_BRANCH)
2. Commit and push your changes
3. When done, open a PR and explain what you built

## Notes

- If git operations fail with "yolo-cage:" messages, that's the dispatcher enforcing rules
- Your user reviews and merges PRs, not you
CLAUDE_EOF
fi
"""],
                    "volumeMounts": [
                        {"name": "workspaces", "mountPath": "/pvc"}
                    ]
                }
            ],
            "containers": [
                {
                    "name": "yolo-cage",
                    "image": "localhost:32000/yolo-cage:latest",
                    "imagePullPolicy": "Always",
                    "env": [
                        {"name": "HOME", "value": "/home/dev"},
                        {"name": "TERM", "value": "xterm-256color"},
                        {"name": "YOLO_CAGE_BRANCH", "value": branch},
                        {"name": "YOLO_CAGE_VERSION", "value": "0.2.0"},
                        {"name": "YOLO_CAGE_DISPATCHER", "value": "http://git-dispatcher:8080"},
                        {"name": "HTTP_PROXY", "value": "http://egress-proxy:8080"},
                        {"name": "HTTPS_PROXY", "value": "http://egress-proxy:8080"},
                        {"name": "http_proxy", "value": "http://egress-proxy:8080"},
                        {"name": "https_proxy", "value": "http://egress-proxy:8080"},
                        {"name": "NO_PROXY", "value": f"localhost,127.0.0.1,.cluster.local,.svc,10.0.0.0/8,git-dispatcher,{PROXY_BYPASS}"},
                        {"name": "no_proxy", "value": f"localhost,127.0.0.1,.cluster.local,.svc,10.0.0.0/8,git-dispatcher,{PROXY_BYPASS}"},
                        {"name": "NODE_EXTRA_CA_CERTS", "value": "/etc/ssl/certs/mitmproxy-ca.pem"},
                        {"name": "REQUESTS_CA_BUNDLE", "value": "/etc/ssl/certs/ca-certificates-combined.crt"},
                        {"name": "SSL_CERT_FILE", "value": "/etc/ssl/certs/ca-certificates-combined.crt"}
                    ],
                    "resources": {
                        "requests": {"cpu": "1", "memory": "4Gi"},
                        "limits": {"cpu": "8", "memory": "32Gi"}
                    },
                    "volumeMounts": [
                        {"name": "workspaces", "mountPath": "/home/dev/workspace", "subPath": branch},
                        {"name": "workspaces", "mountPath": "/home/dev/.claude", "subPath": ".claude"},
                        {"name": "workspaces", "mountPath": "/home/dev/.claude.json", "subPath": ".claude.json"},
                        {"name": "proxy-ca", "mountPath": "/etc/ssl/certs/mitmproxy-ca.pem", "subPath": "mitmproxy-ca.pem", "readOnly": True},
                        {"name": "ca-bundle", "mountPath": "/etc/ssl/certs/ca-certificates-combined.crt", "subPath": "ca-certificates-combined.crt", "readOnly": True},
                        {"name": "agent-prompt", "mountPath": "/config/agent-prompt", "readOnly": True}
                    ]
                }
            ],
            "volumes": [
                {
                    "name": "workspaces",
                    "persistentVolumeClaim": {"claimName": "yolo-cage-workspaces"}
                },
                {
                    "name": "proxy-ca",
                    "configMap": {"name": "proxy-ca"}
                },
                {
                    "name": "ca-bundle",
                    "emptyDir": {}
                },
                {
                    "name": "agent-prompt",
                    "configMap": {"name": "yolo-cage-agent-prompt", "optional": True}
                }
            ]
        }
    }

    return manifest


def create_pod(branch: str) -> PodCreateResponse:
    """Create a new pod for the given branch."""
    v1 = _init_k8s_client()
    pod_name = _pod_name(branch)

    # Check if pod already exists
    try:
        existing = v1.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        return PodCreateResponse(
            name=pod_name,
            branch=branch,
            status=existing.status.phase,
            message=f"Pod already exists. Use 'yolo-cage attach {branch}' to connect."
        )
    except ApiException as e:
        if e.status != 404:
            raise

    # Create the pod
    manifest = _build_pod_manifest(branch)
    logger.info(f"Creating pod {pod_name} for branch {branch}")

    try:
        v1.create_namespaced_pod(namespace=NAMESPACE, body=manifest)
        return PodCreateResponse(
            name=pod_name,
            branch=branch,
            status="Pending",
            message=f"Pod created. Waiting for it to become ready..."
        )
    except ApiException as e:
        logger.error(f"Failed to create pod: {e}")
        raise


def list_pods() -> list[PodInfo]:
    """List all yolo-cage pods."""
    v1 = _init_k8s_client()

    try:
        pods = v1.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector="app=yolo-cage"
        )
    except ApiException as e:
        logger.error(f"Failed to list pods: {e}")
        raise

    result = []
    for pod in pods.items:
        branch = pod.metadata.labels.get("yolo-cage/branch", "unknown")
        result.append(PodInfo(
            name=pod.metadata.name,
            branch=branch,
            status=pod.status.phase,
            ip=pod.status.pod_ip,
            created_at=pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
        ))

    return result


def get_pod(branch: str) -> Optional[PodInfo]:
    """Get a specific pod by branch name."""
    v1 = _init_k8s_client()
    pod_name = _pod_name(branch)

    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        branch_label = pod.metadata.labels.get("yolo-cage/branch", branch)
        return PodInfo(
            name=pod.metadata.name,
            branch=branch_label,
            status=pod.status.phase,
            ip=pod.status.pod_ip,
            created_at=pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
        )
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def delete_pod(branch: str, clean_workspace: bool = False) -> bool:
    """Delete a pod by branch name. Returns True if deleted, False if not found."""
    v1 = _init_k8s_client()
    pod_name = _pod_name(branch)

    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        logger.info(f"Deleted pod {pod_name}")

        if clean_workspace:
            # Delete the workspace directory
            import shutil
            workspace_root = os.environ.get("WORKSPACE_ROOT", "/workspaces")
            workspace_path = os.path.join(workspace_root, branch)
            if os.path.exists(workspace_path):
                shutil.rmtree(workspace_path)
                logger.info(f"Deleted workspace {workspace_path}")

        return True
    except ApiException as e:
        if e.status == 404:
            return False
        raise
