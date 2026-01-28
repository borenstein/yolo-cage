"""Tests for Instance class."""

import json
import pytest
from pathlib import Path

from yolo_cage.instance import Instance


class TestInstancePaths:
    """Tests for Instance path properties."""

    def test_dir(self, tmp_path):
        instance = Instance("test", tmp_path)
        assert instance.dir == tmp_path / "instances" / "test"

    def test_config_path(self, tmp_path):
        instance = Instance("test", tmp_path)
        assert instance.config_path == tmp_path / "instances" / "test" / "config.env"

    def test_repo_dir_cloned(self, tmp_path):
        """Cloned repo uses instances/<name>/repo."""
        instance = Instance("test", tmp_path, repo_path=None)
        assert instance.repo_dir == tmp_path / "instances" / "test" / "repo"

    def test_repo_dir_local(self, tmp_path):
        """Local repo uses specified path."""
        local = tmp_path / "my-repo"
        instance = Instance("test", tmp_path, repo_path=local)
        assert instance.repo_dir == local


class TestInstanceExists:
    """Tests for Instance.exists()."""

    def test_not_exists(self, tmp_path):
        instance = Instance("test", tmp_path)
        assert not instance.exists()

    def test_exists(self, tmp_path):
        inst_dir = tmp_path / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")

        instance = Instance("test", tmp_path)
        assert instance.exists()

    def test_dir_without_json(self, tmp_path):
        inst_dir = tmp_path / "instances" / "test"
        inst_dir.mkdir(parents=True)

        instance = Instance("test", tmp_path)
        assert not instance.exists()


class TestInstanceSave:
    """Tests for Instance.save()."""

    def test_creates_directory(self, tmp_path):
        instance = Instance("test", tmp_path)
        instance.save()
        assert instance.dir.exists()

    def test_writes_metadata_null_repo(self, tmp_path):
        instance = Instance("test", tmp_path, repo_path=None)
        instance.save()

        metadata = json.loads((instance.dir / "instance.json").read_text())
        assert metadata["repo_path"] is None

    def test_writes_metadata_local_repo(self, tmp_path):
        local = tmp_path / "my-repo"
        instance = Instance("test", tmp_path, repo_path=local)
        instance.save()

        metadata = json.loads((instance.dir / "instance.json").read_text())
        assert metadata["repo_path"] == str(local)


class TestInstanceLoad:
    """Tests for Instance.load()."""

    def test_returns_none_if_missing(self, tmp_path):
        assert Instance.load("test", tmp_path) is None

    def test_loads_with_null_repo(self, tmp_path):
        inst_dir = tmp_path / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text('{"repo_path": null}')

        instance = Instance.load("test", tmp_path)
        assert instance is not None
        assert instance.name == "test"
        assert instance._repo_path is None

    def test_loads_with_local_repo(self, tmp_path):
        inst_dir = tmp_path / "instances" / "test"
        inst_dir.mkdir(parents=True)
        local = tmp_path / "my-repo"
        (inst_dir / "instance.json").write_text(f'{{"repo_path": "{local}"}}')

        instance = Instance.load("test", tmp_path)
        assert instance._repo_path == local


class TestInstanceConfig:
    """Tests for Instance.config property."""

    def test_returns_none_if_no_config(self, tmp_path):
        instance = Instance("test", tmp_path)
        instance.save()
        assert instance.config is None

    def test_returns_config(self, tmp_path):
        instance = Instance("test", tmp_path)
        instance.save()
        instance.config_path.write_text(
            "GITHUB_PAT=ghp_test\n"
            "REPO_URL=https://github.com/test/repo\n"
        )

        config = instance.config
        assert config is not None
        assert config.github_pat == "ghp_test"
