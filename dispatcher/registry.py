"""Branch registry - maps pod IPs to assigned branches."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory registry. Production would use ConfigMap or similar.
_registry: dict[str, str] = {}


def register(pod_ip: str, branch: str) -> None:
    """Register a pod for a branch."""
    _registry[pod_ip] = branch
    logger.info(f"Registered pod {pod_ip} for branch {branch}")


def deregister(pod_ip: str) -> Optional[str]:
    """Deregister a pod. Returns the branch it was registered for, or None."""
    branch = _registry.pop(pod_ip, None)
    if branch:
        logger.info(f"Deregistered pod {pod_ip} (was branch {branch})")
    return branch


def get_branch(pod_ip: str) -> Optional[str]:
    """Get the branch assigned to a pod, or None if not registered."""
    return _registry.get(pod_ip)


def list_all() -> dict[str, str]:
    """List all registered pods."""
    return dict(_registry)
