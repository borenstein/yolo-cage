"""Terminal output formatting."""

import sys

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def log_step(msg: str) -> None:
    """Log a step in progress."""
    print(f"{YELLOW}-> {msg}{NC}")


def log_success(msg: str) -> None:
    """Log a successful operation."""
    print(f"{GREEN}OK {msg}{NC}")


def log_error(msg: str) -> None:
    """Log an error to stderr."""
    print(f"{RED}ERROR: {msg}{NC}", file=sys.stderr)


def die(msg: str) -> None:
    """Log error and exit."""
    log_error(msg)
    sys.exit(1)
