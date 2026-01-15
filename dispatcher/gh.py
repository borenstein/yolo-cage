"""GitHub CLI command execution."""

import os
import subprocess

from .config import GITHUB_PAT
from .models import GhResult


def _base_env() -> dict:
    """Get base environment variables for gh execution."""
    env = os.environ.copy()
    # gh CLI uses GITHUB_TOKEN for authentication
    if GITHUB_PAT:
        env["GITHUB_TOKEN"] = GITHUB_PAT
        # Also set GH_TOKEN (gh prefers this)
        env["GH_TOKEN"] = GITHUB_PAT
    # Disable interactive prompts
    env["GH_PROMPT_DISABLED"] = "1"
    # Trust workspace directories regardless of ownership.
    # gh calls git internally, which needs this for the same reason as git.py.
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "safe.directory"
    env["GIT_CONFIG_VALUE_0"] = "*"
    return env


def execute(args: list[str], cwd: str) -> GhResult:
    """Execute a gh CLI command."""
    env = _base_env()

    try:
        result = subprocess.run(
            ["gh"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        return GhResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        return GhResult(
            exit_code=1,
            stdout="",
            stderr="yolo-cage: gh command timed out after 5 minutes",
        )
    except FileNotFoundError:
        return GhResult(
            exit_code=1,
            stdout="",
            stderr="yolo-cage: gh CLI not installed",
        )
    except Exception as e:
        return GhResult(
            exit_code=1,
            stdout="",
            stderr=f"yolo-cage: failed to execute gh: {e}",
        )
