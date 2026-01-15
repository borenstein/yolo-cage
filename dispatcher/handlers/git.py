"""Git command handling and dispatch."""

from fastapi.responses import PlainTextResponse

from ..commands import CommandCategory, classify, get_subcommand
from ..git import execute, execute_with_auth
from ..hooks import run_pre_push_hooks
from ..policy import check_branch_switch, check_merge_allowed, check_push_allowed
from ..responses import denial, command_result


def handle(args: list[str], cwd: str, assigned_branch: str) -> PlainTextResponse:
    """
    Handle a git command with policy enforcement.

    Args:
        args: Git command arguments (e.g., ['commit', '-m', 'msg'])
        cwd: Working directory (dispatcher path, already translated)
        assigned_branch: Branch this pod is allowed to write to

    Returns:
        PlainTextResponse with command output and exit code header
    """
    category, deny_message = classify(args)

    if category == CommandCategory.DENIED:
        return denial(deny_message + "\n")

    if category == CommandCategory.UNKNOWN:
        return denial("yolo-cage: unrecognized or disallowed git operation\n")

    # Branch switch: execute but warn if switching away
    if category == CommandCategory.BRANCH:
        warning = check_branch_switch(args, assigned_branch)
        result = execute(args, cwd)
        output = (warning + "\n" if warning else "") + result.stdout + result.stderr
        return command_result(output, result.exit_code)

    # Merge: must be on assigned branch
    if category == CommandCategory.MERGE:
        error = check_merge_allowed(cwd, assigned_branch, get_subcommand(args))
        if error:
            return denial(error)
        result = execute(args, cwd)
        return command_result(result.stdout + result.stderr, result.exit_code)

    # Push: branch enforcement + pre-push hooks
    if category == CommandCategory.REMOTE_WRITE:
        error = check_push_allowed(args, cwd, assigned_branch)
        if error:
            return denial(error)

        hook_ok, hook_output = run_pre_push_hooks(cwd)
        if not hook_ok:
            return denial(f"yolo-cage: push rejected by pre-push hooks\n\n{hook_output}")

        result = execute_with_auth(args, cwd)
        return command_result(result.stdout + result.stderr, result.exit_code)

    # Remote read (fetch/pull): just needs auth
    if category == CommandCategory.REMOTE_READ:
        result = execute_with_auth(args, cwd)
        return command_result(result.stdout + result.stderr, result.exit_code)

    # Local operations: no restrictions
    result = execute(args, cwd)
    return command_result(result.stdout + result.stderr, result.exit_code)
