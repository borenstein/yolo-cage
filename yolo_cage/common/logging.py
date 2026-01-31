"""Logging utilities - Consistent output formatting."""

import sys

# Colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"  # No Color


def log_step(msg: str) -> None:
    """Log a step in progress.

    Args:
        msg: Step message
    """
    print(f"{YELLOW}-> {msg}{NC}")


def log_success(msg: str) -> None:
    """Log a successful operation.

    Args:
        msg: Success message
    """
    print(f"{GREEN}OK {msg}{NC}")


def log_error(msg: str) -> None:
    """Log an error message.

    Args:
        msg: Error message
    """
    print(f"{RED}ERROR: {msg}{NC}", file=sys.stderr)


def die(msg: str) -> None:
    """Log error and exit with code 1.

    Args:
        msg: Error message
    """
    log_error(msg)
    sys.exit(1)
