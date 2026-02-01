"""Shared pytest fixtures for yolo-cage tests."""

import os
import pytest
from pathlib import Path


@pytest.fixture
def temp_yolo_cage_home(tmp_path, monkeypatch):
    """Create a temporary yolo-cage home directory structure.

    Sets YOLO_CAGE_HOME to point to the temporary directory.

    Returns:
        Path to ~/.yolo-cage equivalent
    """
    home = tmp_path / ".yolo-cage"
    home.mkdir(parents=True)
    monkeypatch.setenv("YOLO_CAGE_HOME", str(home))
    return home
