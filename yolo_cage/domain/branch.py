"""Branch value object - Represents a git branch in the managed repository."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Branch:
    """A git branch name in the managed repository.

    Branch is immutable and provides transformation to pod name format.
    """

    name: str

    def __post_init__(self) -> None:
        """Validate branch name."""
        if not self.name:
            raise ValueError("Branch name cannot be empty")

        if self.name.startswith("-"):
            raise ValueError("Branch name cannot start with -")

    def to_pod_name(self) -> str:
        """Transform branch name to valid Kubernetes pod name.

        Kubernetes pod names must:
        - Be lowercase
        - Use hyphens instead of slashes or underscores
        - Start with yolo-cage- prefix

        Examples:
            feature/auth -> yolo-cage-feature-auth
            BUGFIX_123 -> yolo-cage-bugfix-123
        """
        normalized = self.name.lower()
        normalized = normalized.replace("/", "-").replace("_", "-")
        return f"yolo-cage-{normalized}"

    @classmethod
    def from_pod_name(cls, pod_name: str) -> "Branch":
        """Extract branch name from pod name.

        Args:
            pod_name: Pod name in format yolo-cage-{branch}

        Returns:
            Branch instance

        Raises:
            ValueError: If pod name doesn't match expected format
        """
        if not pod_name.startswith("yolo-cage-"):
            raise ValueError(f"Invalid pod name format: {pod_name}")

        branch_part = pod_name[len("yolo-cage-"):]
        if not branch_part:
            raise ValueError(f"Invalid pod name format: {pod_name}")

        # Note: This is lossy - we can't perfectly reverse the transformation
        # since we don't know if hyphens were originally slashes/underscores
        return cls(name=branch_part)

    def __str__(self) -> str:
        return self.name
