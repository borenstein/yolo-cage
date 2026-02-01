"""Tests for instance management functions."""

import json
import pytest
from pathlib import Path

from yolo_cage.host import instances


class TestListInstances:
    """Tests for list_instances()."""

    def test_empty_when_no_instances(self, temp_yolo_cage_home):
        """list_instances() returns empty list when no instances exist."""
        assert instances.list_instances() == []

    def test_returns_sorted_names(self, temp_yolo_cage_home):
        """list_instances() returns sorted list of instance names."""
        instances_dir = temp_yolo_cage_home / "instances"
        for name in ["zebra", "alpha", "beta"]:
            (instances_dir / name).mkdir(parents=True)
            (instances_dir / name / "instance.json").write_text("{}")

        result = instances.list_instances()
        assert result == ["alpha", "beta", "zebra"]

    def test_ignores_dirs_without_instance_json(self, temp_yolo_cage_home):
        """list_instances() ignores directories without instance.json."""
        instances_dir = temp_yolo_cage_home / "instances"
        (instances_dir / "valid").mkdir(parents=True)
        (instances_dir / "valid" / "instance.json").write_text("{}")
        (instances_dir / "invalid").mkdir(parents=True)  # No instance.json

        result = instances.list_instances()
        assert result == ["valid"]


class TestInstanceExists:
    """Tests for instance_exists()."""

    def test_false_when_not_exists(self, temp_yolo_cage_home):
        """instance_exists() returns False when instance doesn't exist."""
        assert not instances.instance_exists("nonexistent")

    def test_true_when_exists(self, temp_yolo_cage_home):
        """instance_exists() returns True when instance.json exists."""
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")

        assert instances.instance_exists("test")


class TestGetPaths:
    """Tests for path getter functions."""

    def test_get_instance_dir(self, temp_yolo_cage_home):
        """get_instance_dir() returns correct path."""
        result = instances.get_instance_dir("test")
        assert result == temp_yolo_cage_home / "instances" / "test"

    def test_get_config_path(self, temp_yolo_cage_home):
        """get_config_path() returns correct path."""
        result = instances.get_config_path("test")
        assert result == temp_yolo_cage_home / "instances" / "test" / "config.env"

    def test_get_repo_dir_without_repo_path(self, temp_yolo_cage_home):
        """get_repo_dir() returns cloned repo path when repo_path is None."""
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text('{"repo_path": null}')

        result = instances.get_repo_dir("test")
        assert result == instance_dir / "repo"

    def test_get_repo_dir_with_repo_path(self, temp_yolo_cage_home):
        """get_repo_dir() returns repo_path when set."""
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text('{"repo_path": "/dev/path"}')

        result = instances.get_repo_dir("test")
        assert result == Path("/dev/path")


class TestDefault:
    """Tests for get_default() and set_default()."""

    def test_get_default_none_initially(self, temp_yolo_cage_home):
        """get_default() returns None when not set."""
        assert instances.get_default() is None

    def test_set_and_get_default(self, temp_yolo_cage_home):
        """set_default() sets the default instance."""
        # Create instance first
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")

        instances.set_default("test")

        assert instances.get_default() == "test"

    def test_set_default_nonexistent_exits(self, temp_yolo_cage_home):
        """set_default() exits for nonexistent instance."""
        with pytest.raises(SystemExit):
            instances.set_default("nonexistent")

    def test_get_default_clears_if_instance_deleted(self, temp_yolo_cage_home):
        """get_default() returns None if default instance was deleted."""
        (temp_yolo_cage_home / "default").write_text("deleted\n")

        assert instances.get_default() is None


class TestResolve:
    """Tests for resolve()."""

    def test_resolve_explicit_name(self, temp_yolo_cage_home):
        """resolve() with explicit name returns that name."""
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")

        result = instances.resolve("test")
        assert result == "test"

    def test_resolve_explicit_name_not_found(self, temp_yolo_cage_home):
        """resolve() with nonexistent name exits."""
        with pytest.raises(SystemExit):
            instances.resolve("nonexistent")

    def test_resolve_no_instances(self, temp_yolo_cage_home):
        """resolve() with no instances exits."""
        with pytest.raises(SystemExit):
            instances.resolve(None)

    def test_resolve_single_instance(self, temp_yolo_cage_home):
        """resolve() with single instance returns it automatically."""
        instance_dir = temp_yolo_cage_home / "instances" / "only-one"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")

        result = instances.resolve(None)
        assert result == "only-one"

    def test_resolve_multiple_with_default(self, temp_yolo_cage_home):
        """resolve() with multiple instances uses default."""
        for name in ["alpha", "beta"]:
            instance_dir = temp_yolo_cage_home / "instances" / name
            instance_dir.mkdir(parents=True)
            (instance_dir / "instance.json").write_text("{}")

        instances.set_default("beta")

        result = instances.resolve(None)
        assert result == "beta"

    def test_resolve_multiple_no_default(self, temp_yolo_cage_home):
        """resolve() with multiple instances and no default exits."""
        for name in ["alpha", "beta"]:
            instance_dir = temp_yolo_cage_home / "instances" / name
            instance_dir.mkdir(parents=True)
            (instance_dir / "instance.json").write_text("{}")

        with pytest.raises(SystemExit):
            instances.resolve(None)


class TestCreate:
    """Tests for create()."""

    def test_create_new_instance(self, temp_yolo_cage_home, mocker):
        """create() creates a new instance."""
        # Mock git clone since we don't want to actually clone
        mocker.patch("subprocess.run")

        result = instances.create("test")

        assert result == temp_yolo_cage_home / "instances" / "test"
        assert instances.instance_exists("test")

    def test_create_with_repo_path(self, temp_yolo_cage_home):
        """create() stores repo_path and doesn't clone."""
        dev_repo = Path("/dev/path")
        result = instances.create("test", repo_path=dev_repo)

        instance_json = temp_yolo_cage_home / "instances" / "test" / "instance.json"
        data = json.loads(instance_json.read_text())
        assert data["repo_path"] == str(dev_repo)

    def test_create_existing_exits(self, temp_yolo_cage_home):
        """create() exits for existing instance."""
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")

        with pytest.raises(SystemExit):
            instances.create("test")


class TestDelete:
    """Tests for delete()."""

    def test_delete_instance(self, temp_yolo_cage_home):
        """delete() removes instance directory."""
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")

        instances.delete("test")

        assert not instances.instance_exists("test")

    def test_delete_nonexistent_exits(self, temp_yolo_cage_home):
        """delete() exits for nonexistent instance."""
        with pytest.raises(SystemExit):
            instances.delete("nonexistent")

    def test_delete_clears_default(self, temp_yolo_cage_home):
        """delete() clears default if deleting default instance."""
        instance_dir = temp_yolo_cage_home / "instances" / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")
        instances.set_default("test")

        instances.delete("test")

        assert instances.get_default() is None


class TestMigrateLegacy:
    """Tests for migrate_legacy()."""

    def test_migrate_nothing_to_migrate(self, temp_yolo_cage_home):
        """migrate_legacy() returns False when nothing to migrate."""
        assert not instances.migrate_legacy()

    def test_migrate_already_has_instances(self, temp_yolo_cage_home):
        """migrate_legacy() returns False when instances already exist."""
        # Create an instance (new layout)
        instance_dir = temp_yolo_cage_home / "instances" / "existing"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")

        # Create old-style files
        (temp_yolo_cage_home / "config.env").write_text("GITHUB_PAT=test")

        # Should not migrate because instances already exist
        assert not instances.migrate_legacy()

    def test_migrate_config_only(self, temp_yolo_cage_home):
        """migrate_legacy() migrates config.env to default instance."""
        old_config = temp_yolo_cage_home / "config.env"
        old_config.write_text("GITHUB_PAT=test\nREPO_URL=test")

        result = instances.migrate_legacy()

        assert result is True
        assert not old_config.exists()

        # Check new location
        new_config = temp_yolo_cage_home / "instances" / "default" / "config.env"
        assert new_config.exists()
        assert new_config.read_text() == "GITHUB_PAT=test\nREPO_URL=test"

        # Check default is set
        assert instances.get_default() == "default"

    def test_migrate_repo_only(self, temp_yolo_cage_home):
        """migrate_legacy() migrates repo/ to default instance."""
        old_repo = temp_yolo_cage_home / "repo"
        old_repo.mkdir()
        (old_repo / "Vagrantfile").write_text("# test")

        result = instances.migrate_legacy()

        assert result is True
        assert not old_repo.exists()

        # Check new location
        new_repo = temp_yolo_cage_home / "instances" / "default" / "repo"
        assert new_repo.is_dir()
        assert (new_repo / "Vagrantfile").exists()

    def test_migrate_both(self, temp_yolo_cage_home):
        """migrate_legacy() migrates both config.env and repo/."""
        old_config = temp_yolo_cage_home / "config.env"
        old_config.write_text("GITHUB_PAT=test")

        old_repo = temp_yolo_cage_home / "repo"
        old_repo.mkdir()
        (old_repo / "Vagrantfile").write_text("# test")

        result = instances.migrate_legacy()

        assert result is True
        assert not old_config.exists()
        assert not old_repo.exists()

        default_dir = temp_yolo_cage_home / "instances" / "default"
        assert (default_dir / "config.env").exists()
        assert (default_dir / "repo").is_dir()
        assert instances.get_default() == "default"
