"""GitHub CLI command execution."""

import os
import subprocess
import tempfile
from typing import Optional

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


def _rewrite_args_with_temp_files(
    args: list[str],
    files: dict[str, str],
    stdin_content: Optional[str],
) -> tuple[list[str], list[str]]:
    """Rewrite args to use temp files for transmitted file content.

    Args:
        args: Original command arguments
        files: Map of original path -> content (from --body-file <path>)
        stdin_content: Content for --body-file - (stdin)

    Returns:
        Tuple of (rewritten args, list of temp file paths to clean up)
    """
    temp_files = []
    new_args = []
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "--body-file" and i + 1 < len(args):
            filepath = args[i + 1]

            if filepath == "-" and stdin_content is not None:
                # Create temp file for stdin content
                fd, temp_path = tempfile.mkstemp(suffix=".md", prefix="gh-body-")
                os.write(fd, stdin_content.encode("utf-8"))
                os.close(fd)
                temp_files.append(temp_path)
                new_args.append("--body-file")
                new_args.append(temp_path)
                i += 2
                continue

            elif filepath in files:
                # Create temp file for transmitted file content
                fd, temp_path = tempfile.mkstemp(suffix=".md", prefix="gh-body-")
                os.write(fd, files[filepath].encode("utf-8"))
                os.close(fd)
                temp_files.append(temp_path)
                new_args.append("--body-file")
                new_args.append(temp_path)
                i += 2
                continue

        new_args.append(arg)
        i += 1

    return new_args, temp_files


def execute(
    args: list[str],
    cwd: str,
    files: Optional[dict[str, str]] = None,
    stdin_content: Optional[str] = None,
) -> GhResult:
    """Execute a gh CLI command.

    Args:
        args: Command arguments
        cwd: Working directory
        files: Map of path -> content for --body-file arguments
        stdin_content: Content for --body-file - (stdin)

    Returns:
        GhResult with exit code, stdout, stderr
    """
    env = _base_env()
    files = files or {}
    temp_files = []

    try:
        # Rewrite args to use temp files for transmitted content
        exec_args, temp_files = _rewrite_args_with_temp_files(
            args, files, stdin_content
        )

        result = subprocess.run(
            ["gh"] + exec_args,
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
    finally:
        # Clean up temp files
        for temp_path in temp_files:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
