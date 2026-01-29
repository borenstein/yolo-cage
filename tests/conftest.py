"""Shared test fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_yolo_home(tmp_path, monkeypatch):
    """Set YOLO_CAGE_HOME to a temp directory."""
    home = tmp_path / ".yolo-cage"
    home.mkdir()
    monkeypatch.setenv("YOLO_CAGE_HOME", str(home))
    return home


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a fake yolo-cage repo with Vagrantfile."""
    repo = tmp_path / "yolo-cage"
    repo.mkdir()
    (repo / "Vagrantfile").touch()
    (repo / "scripts").mkdir()
    return repo


@pytest.fixture
def instance_with_config(tmp_yolo_home):
    """Create an instance with a config file."""
    instances_dir = tmp_yolo_home / "instances"
    default_dir = instances_dir / "default"
    default_dir.mkdir(parents=True)

    # Create instance.json
    (default_dir / "instance.json").write_text('{"repo_path": null}\n')

    # Create config.env
    (default_dir / "config.env").write_text(
        "GITHUB_PAT=test_pat\n"
        "REPO_URL=https://github.com/test/repo\n"
        "GIT_NAME=test\n"
        "GIT_EMAIL=test@example.com\n"
    )

    # Create repo dir
    repo_dir = default_dir / "repo"
    repo_dir.mkdir()
    (repo_dir / "Vagrantfile").touch()

    # Set as default
    (tmp_yolo_home / "default").write_text("default\n")

    return default_dir
