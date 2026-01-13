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
