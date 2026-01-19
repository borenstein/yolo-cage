"""Git command execution."""

import os
import subprocess
from typing import Optional

from .config import GIT_USER_NAME, GIT_USER_EMAIL, GITHUB_PAT
from .models import GitResult


def _safe_directory_env() -> dict:
    """Get environment variables for safe directory access."""
    env = os.environ.copy()
    # Trust workspace directories regardless of ownership.
    # Kubernetes creates subPath mount directories as root before the
    # dispatcher (running as uid 1000) can clone into them.
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "safe.directory"
    env["GIT_CONFIG_VALUE_0"] = "*"
    return env


def get_current_branch(cwd: str) -> Optional[str]:
    """Get the current branch in the given working directory."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            env=_safe_directory_env(),
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            # "HEAD" means detached HEAD state
            return branch if branch != "HEAD" else None
        else:
            logger.warning(f"git rev-parse failed in {cwd}: {result.stderr.strip()}")
    except FileNotFoundError:
        logger.warning(f"Directory does not exist: {cwd}")
    except Exception as e:
        logger.warning(f"Failed to get branch in {cwd}: {e}")
    return None


def _base_env() -> dict:
    """Get base environment variables for git execution."""
    env = _safe_directory_env()
    env["GIT_AUTHOR_NAME"] = GIT_USER_NAME
    env["GIT_AUTHOR_EMAIL"] = GIT_USER_EMAIL
    env["GIT_COMMITTER_NAME"] = GIT_USER_NAME
    env["GIT_COMMITTER_EMAIL"] = GIT_USER_EMAIL
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _run_git(args: list[str], cwd: str, env: dict) -> GitResult:
    """Run a git command with the given environment."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        return GitResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        return GitResult(
            exit_code=1,
            stdout="",
            stderr="yolo-cage: git command timed out after 5 minutes",
        )
    except Exception as e:
        return GitResult(
            exit_code=1,
            stdout="",
            stderr=f"yolo-cage: failed to execute git: {e}",
        )


def execute(args: list[str], cwd: str) -> GitResult:
    """Execute a git command (no authentication)."""
    return _run_git(args, cwd, _base_env())


def execute_with_auth(args: list[str], cwd: str) -> GitResult:
    """Execute a git command with GitHub authentication."""
    env = _base_env()

    if not GITHUB_PAT:
        return _run_git(args, cwd, env)

    # Use GIT_ASKPASS to provide credentials
    askpass_script = "/tmp/git-askpass.sh"
    try:
        with open(askpass_script, "w") as f:
            f.write(f"#!/bin/bash\necho {GITHUB_PAT}\n")
        os.chmod(askpass_script, 0o700)
        env["GIT_ASKPASS"] = askpass_script

        return _run_git(args, cwd, env)
    finally:
        if os.path.exists(askpass_script):
            os.remove(askpass_script)
