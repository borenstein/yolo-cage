"""HTTP response formatting for command results."""

from fastapi.responses import PlainTextResponse


def denial(message: str) -> PlainTextResponse:
    """Create a denial response with exit code 1."""
    return PlainTextResponse(
        content=message,
        headers={"X-Yolo-Cage-Exit-Code": "1"},
    )


def command_result(output: str, exit_code: int) -> PlainTextResponse:
    """Create a response with command output and exit code."""
    return PlainTextResponse(
        content=output,
        headers={"X-Yolo-Cage-Exit-Code": str(exit_code)},
    )
