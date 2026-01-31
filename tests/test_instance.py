"""Tests for Instance class."""

import json
import pytest
from pathlib import Path

from yolo_cage.host.instance import Instance


@pytest.fixture
def temp_home(tmp_path):
    """Create a temporary yolo-cage home directory."""
    return tmp_path / ".yolo-cage"


class TestInstance:
    """Tests for Instance value object."""

    def test_dir_path(self, temp_home):
        """Instance.dir returns correct path."""
        instance = Instance(name="test", home=temp_home)
        assert instance.dir == temp_home / "instances" / "test"

    def test_config_path(self, temp_home):
        """Instance.config_path returns correct path."""
        instance = Instance(name="test", home=temp_home)
        assert instance.config_path == temp_home / "instances" / "test" / "config.env"

    def test_repo_dir_without_repo_path(self, temp_home):
        """Instance.repo_dir returns cloned repo path when repo_path is None."""
        instance = Instance(name="test", home=temp_home, repo_path=None)
        assert instance.repo_dir == temp_home / "instances" / "test" / "repo"

    def test_repo_dir_with_repo_path(self, temp_home):
        """Instance.repo_dir returns repo_path when set."""
        dev_repo = Path("/home/user/dev/yolo-cage")
        instance = Instance(name="test", home=temp_home, repo_path=dev_repo)
        assert instance.repo_dir == dev_repo

    def test_exists_false_when_not_created(self, temp_home):
        """Instance.exists() returns False when instance doesn't exist."""
        instance = Instance(name="test", home=temp_home)
        assert not instance.exists()

    def test_exists_true_when_created(self, temp_home):
        """Instance.exists() returns True when instance directory exists."""
        instance = Instance(name="test", home=temp_home)
        instance.dir.mkdir(parents=True)
        assert instance.exists()

    def test_save_creates_instance_json(self, temp_home):
        """Instance.save() creates instance.json with metadata."""
        instance = Instance(name="test", home=temp_home)
        instance.save()

        assert instance.instance_json_path.exists()
        with open(instance.instance_json_path) as f:
            metadata = json.load(f)
        assert metadata == {"repo_path": None}

    def test_save_with_repo_path(self, temp_home):
        """Instance.save() stores repo_path in instance.json."""
        dev_repo = Path("/home/user/dev/yolo-cage")
        instance = Instance(name="test", home=temp_home, repo_path=dev_repo)
        instance.save()

        with open(instance.instance_json_path) as f:
            metadata = json.load(f)
        assert metadata == {"repo_path": str(dev_repo)}

    def test_load_returns_none_for_nonexistent(self, temp_home):
        """Instance.load() returns None when instance doesn't exist."""
        result = Instance.load("nonexistent", temp_home)
        assert result is None

    def test_load_returns_instance(self, temp_home):
        """Instance.load() returns Instance when it exists."""
        # Create instance first
        instance = Instance(name="test", home=temp_home)
        instance.save()

        # Load it
        loaded = Instance.load("test", temp_home)
        assert loaded is not None
        assert loaded.name == "test"
        assert loaded.home == temp_home
        assert loaded.repo_path is None

    def test_load_restores_repo_path(self, temp_home):
        """Instance.load() restores repo_path from instance.json."""
        dev_repo = Path("/home/user/dev/yolo-cage")
        instance = Instance(name="test", home=temp_home, repo_path=dev_repo)
        instance.save()

        loaded = Instance.load("test", temp_home)
        assert loaded is not None
        assert loaded.repo_path == dev_repo

    def test_config_returns_none_when_no_config(self, temp_home):
        """Instance.config() returns None when config.env doesn't exist."""
        instance = Instance(name="test", home=temp_home)
        instance.save()

        assert instance.config() is None

    def test_config_loads_config_file(self, temp_home):
        """Instance.config() loads Config from config.env."""
        instance = Instance(name="test", home=temp_home)
        instance.save()

        # Create config.env
        config_content = """GITHUB_PAT=test-pat
REPO_URL=https://github.com/user/repo
GIT_NAME=Test User
GIT_EMAIL=test@example.com
"""
        instance.config_path.write_text(config_content)

        config = instance.config()
        assert config is not None
        assert config.github_pat == "test-pat"
        assert config.repo_url == "https://github.com/user/repo"
        assert config.git_name == "Test User"
        assert config.git_email == "test@example.com"
