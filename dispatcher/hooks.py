"""Pre-push hook execution."""

import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

from .config import PRE_PUSH_HOOKS

logger = logging.getLogger(__name__)


@dataclass
class HookResult:
    """Result of running a single hook."""
    success: bool
    output: str
    hook_cmd: str


def _run_single_hook(hook_cmd: str, cwd: str) -> HookResult:
    """Run a single hook command. Returns HookResult."""
    logger.info(f"Running pre-push hook: {hook_cmd}")
    try:
        result = subprocess.run(
            hook_cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        return HookResult(
            success=(result.returncode == 0),
            output=output,
            hook_cmd=hook_cmd,
        )
    except subprocess.TimeoutExpired:
        return HookResult(
            success=False,
            output=f"Hook timed out: {hook_cmd}",
            hook_cmd=hook_cmd,
        )
    except Exception as e:
        return HookResult(
            success=False,
            output=f"Hook failed: {hook_cmd}: {e}",
            hook_cmd=hook_cmd,
        )


def run_pre_push_hooks(cwd: str) -> tuple[bool, str]:
    """
    Run all pre-push hooks.

    Returns (success, combined_output).
    """
    if not PRE_PUSH_HOOKS:
        return True, ""

    outputs = []
    for hook_cmd in PRE_PUSH_HOOKS:
        result = _run_single_hook(hook_cmd, cwd)
        if result.output:
            outputs.append(result.output)
        if not result.success:
            logger.warning(f"Pre-push hook failed: {result.hook_cmd}")
            return False, "\n".join(outputs)

    return True, "\n".join(outputs)
