"""Tests for output module."""

import pytest
from yolo_cage.output import log_step, log_success, log_error, die, YELLOW, GREEN, RED, NC


def test_log_step(capsys):
    """log_step prints yellow arrow prefix."""
    log_step("test message")
    captured = capsys.readouterr()
    assert f"{YELLOW}-> test message{NC}" in captured.out


def test_log_success(capsys):
    """log_success prints green OK prefix."""
    log_success("test message")
    captured = capsys.readouterr()
    assert f"{GREEN}OK test message{NC}" in captured.out


def test_log_error(capsys):
    """log_error prints red ERROR prefix to stderr."""
    log_error("test message")
    captured = capsys.readouterr()
    assert f"{RED}ERROR: test message{NC}" in captured.err


def test_die_exits_with_error(capsys):
    """die prints error and exits with code 1."""
    with pytest.raises(SystemExit) as exc_info:
        die("fatal error")
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "ERROR: fatal error" in captured.err
