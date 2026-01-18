"""Request and response models."""

from typing import Optional
from pydantic import BaseModel


class GitRequest(BaseModel):
    """Request from git shim in sandbox pod."""
    args: list[str]
    cwd: str


class GitResult(BaseModel):
    """Result of a git operation."""
    exit_code: int
    stdout: str
    stderr: str


class PolicyViolation(BaseModel):
    """A branch policy violation."""
    message: str


class GhRequest(BaseModel):
    """Request from gh shim in sandbox pod."""
    args: list[str]
    cwd: str


class GhResult(BaseModel):
    """Result of a gh operation."""
    exit_code: int
    stdout: str
    stderr: str


class PodCreateRequest(BaseModel):
    """Request to create a new pod."""
    branch: str


class PodInfo(BaseModel):
    """Information about a pod."""
    name: str
    branch: str
    status: str
    ip: Optional[str] = None
    created_at: Optional[str] = None


class PodListResponse(BaseModel):
    """List of pods."""
    pods: list[PodInfo]


class PodCreateResponse(BaseModel):
    """Response from pod creation."""
    name: str
    branch: str
    status: str
    message: str
