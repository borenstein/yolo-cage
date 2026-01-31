"""Shared pytest fixtures for yolo-cage tests."""

import pytest
from pathlib import Path


@pytest.fixture
def temp_yolo_cage_home(tmp_path):
    """Create a temporary yolo-cage home directory structure.

    Returns:
        Path to ~/.yolo-cage equivalent
    """
    home = tmp_path / ".yolo-cage"
    home.mkdir(parents=True)
    return home
