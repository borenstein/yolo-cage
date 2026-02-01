"""Sandbox entity - Represents an isolated environment bound to a branch."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .branch import Branch


class SandboxStatus(Enum):
    """Sandbox lifecycle status."""

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"

    @classmethod
    def from_pod_phase(cls, phase: str) -> "SandboxStatus":
        """Convert Kubernetes pod phase to sandbox status.

        Args:
            phase: Pod phase (Pending, Running, Succeeded, Failed, Unknown)

        Returns:
            SandboxStatus
        """
        try:
            return cls(phase)
        except ValueError:
            return cls.UNKNOWN


@dataclass
class Sandbox:
    """An isolated environment for an agent to work on a specific branch.

    Attributes:
        branch: The assigned branch this sandbox works on
        status: Current lifecycle status
        pod_name: Kubernetes pod name (derived from branch)
        age: Human-readable age string (e.g., "2h", "5m")
    """

    branch: Branch
    status: SandboxStatus
    age: Optional[str] = None

    @property
    def pod_name(self) -> str:
        """The Kubernetes pod name for this sandbox."""
        return self.branch.to_pod_name()

    def __str__(self) -> str:
        age_str = f" (age: {self.age})" if self.age else ""
        return f"Sandbox[{self.branch.name}] - {self.status.value}{age_str}"
