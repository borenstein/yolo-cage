"""GitHub CLI command handling and dispatch."""

from fastapi.responses import PlainTextResponse

from ..gh import execute as gh_execute
from ..gh_commands import GhCommandCategory, classify_gh
from ..responses import denial, command_result


def handle(args: list[str], cwd: str) -> PlainTextResponse:
    """
    Handle a gh CLI command with policy enforcement.

    Args:
        args: GH command arguments (e.g., ['pr', 'create', '--title', 'Fix'])
        cwd: Working directory (dispatcher path, already translated)

    Returns:
        PlainTextResponse with command output and exit code header
    """
    category, deny_message = classify_gh(args)

    if category == GhCommandCategory.BLOCKED:
        return denial(deny_message + "\n")

    if category == GhCommandCategory.UNKNOWN:
        return denial("yolo-cage: unrecognized or disallowed gh operation\n")

    # Allowed: execute with authentication
    result = gh_execute(args, cwd)
    return command_result(result.stdout + result.stderr, result.exit_code)
