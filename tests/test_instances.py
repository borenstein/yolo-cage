"""Tests for instance management."""

import json
import pytest
from pathlib import Path

from yolo_cage.instances import (
    list_instances,
    get_default_instance,
    set_default_instance,
    get_instance_config,
    get_repo_dir,
    get_config_path,
    instance_exists,
    create_instance,
    delete_instance,
    resolve_instance,
    maybe_migrate_legacy_layout,
    get_instances_dir,
    get_yolo_cage_home,
)


class TestListInstances:
    """Tests for list_instances function."""

    def test_no_instances_dir(self, tmp_yolo_home):
        """Returns empty list when instances dir doesn't exist."""
        assert list_instances() == []

    def test_empty_instances_dir(self, tmp_yolo_home):
        """Returns empty list when instances dir is empty."""
        (tmp_yolo_home / "instances").mkdir()
        assert list_instances() == []

    def test_lists_valid_instances(self, tmp_yolo_home):
        """Returns list of valid instance names."""
        instances_dir = tmp_yolo_home / "instances"
        instances_dir.mkdir()

        # Create valid instance
        (instances_dir / "foo").mkdir()
        (instances_dir / "foo" / "instance.json").write_text("{}")

        # Create invalid (no instance.json)
        (instances_dir / "invalid").mkdir()

        assert list_instances() == ["foo"]

    def test_sorted_alphabetically(self, tmp_yolo_home):
        """Instances are sorted alphabetically."""
        instances_dir = tmp_yolo_home / "instances"
        instances_dir.mkdir()

        for name in ["zebra", "alpha", "middle"]:
            (instances_dir / name).mkdir()
            (instances_dir / name / "instance.json").write_text("{}")

        assert list_instances() == ["alpha", "middle", "zebra"]


class TestDefaultInstance:
    """Tests for default instance management."""

    def test_no_default(self, tmp_yolo_home):
        """Returns None when no default file exists."""
        assert get_default_instance() is None

    def test_empty_default_file(self, tmp_yolo_home):
        """Returns None when default file is empty."""
        (tmp_yolo_home / "default").write_text("")
        assert get_default_instance() is None

    def test_default_instance_not_exists(self, tmp_yolo_home):
        """Returns None when default instance no longer exists."""
        (tmp_yolo_home / "default").write_text("deleted")
        assert get_default_instance() is None

    def test_get_and_set_default(self, tmp_yolo_home):
        """Can set and get default instance."""
        # Create the instance first
        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "myinstance").mkdir(parents=True)
        (instances_dir / "myinstance" / "instance.json").write_text("{}")

        set_default_instance("myinstance")
        assert get_default_instance() == "myinstance"

    def test_set_default_creates_directory(self, tmp_path, monkeypatch):
        """set_default creates parent directory if needed."""
        home = tmp_path / "new-home" / ".yolo-cage"
        monkeypatch.setenv("YOLO_CAGE_HOME", str(home))

        # Create instance
        (home / "instances" / "test").mkdir(parents=True)
        (home / "instances" / "test" / "instance.json").write_text("{}")

        set_default_instance("test")
        assert (home / "default").exists()


class TestInstanceConfig:
    """Tests for instance configuration."""

    def test_get_config_nonexistent(self, tmp_yolo_home):
        """Returns empty dict for nonexistent instance."""
        assert get_instance_config("nonexistent") == {}

    def test_get_config_exists(self, tmp_yolo_home):
        """Returns config from instance.json."""
        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "test").mkdir(parents=True)
        (instances_dir / "test" / "instance.json").write_text(
            '{"repo_path": "/some/path"}'
        )

        config = get_instance_config("test")
        assert config == {"repo_path": "/some/path"}


class TestRepoDir:
    """Tests for get_repo_dir function."""

    def test_cloned_repo(self, tmp_yolo_home):
        """Returns instances/<name>/repo for cloned repos."""
        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "test").mkdir(parents=True)
        (instances_dir / "test" / "instance.json").write_text('{"repo_path": null}')

        repo_dir = get_repo_dir("test")
        assert repo_dir == instances_dir / "test" / "repo"

    def test_local_repo(self, tmp_yolo_home, tmp_path):
        """Returns stored path for local repos."""
        local_path = tmp_path / "my-repo"

        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "test").mkdir(parents=True)
        (instances_dir / "test" / "instance.json").write_text(
            f'{{"repo_path": "{local_path}"}}'
        )

        repo_dir = get_repo_dir("test")
        assert repo_dir == local_path


class TestInstanceExists:
    """Tests for instance_exists function."""

    def test_not_exists(self, tmp_yolo_home):
        """Returns False for nonexistent instance."""
        assert instance_exists("nonexistent") is False

    def test_exists(self, tmp_yolo_home):
        """Returns True for existing instance."""
        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "test").mkdir(parents=True)
        (instances_dir / "test" / "instance.json").write_text("{}")

        assert instance_exists("test") is True

    def test_dir_without_json(self, tmp_yolo_home):
        """Returns False when directory exists but instance.json doesn't."""
        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "test").mkdir(parents=True)

        assert instance_exists("test") is False


class TestCreateInstance:
    """Tests for create_instance function."""

    def test_create_with_local_repo(self, tmp_yolo_home, tmp_path):
        """Creates instance with local repo path."""
        local_repo = tmp_path / "my-repo"
        local_repo.mkdir()

        instance_dir = create_instance("test", repo_path=local_repo)

        assert instance_dir == get_instances_dir() / "test"
        config = json.loads((instance_dir / "instance.json").read_text())
        assert config["repo_path"] == str(local_repo)

    def test_create_sets_null_repo_path_for_clone(self, tmp_yolo_home, mocker):
        """Creates instance with null repo_path for cloned repo."""
        # Mock git clone
        mocker.patch("subprocess.run")

        instance_dir = create_instance("test")

        config = json.loads((instance_dir / "instance.json").read_text())
        assert config["repo_path"] is None


class TestDeleteInstance:
    """Tests for delete_instance function."""

    def test_delete_removes_directory(self, tmp_yolo_home):
        """Delete removes instance directory."""
        instances_dir = tmp_yolo_home / "instances"
        instance_dir = instances_dir / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")
        (instance_dir / "config.env").write_text("KEY=value")

        delete_instance("test")

        assert not instance_dir.exists()

    def test_delete_clears_default_if_current(self, tmp_yolo_home):
        """Delete clears default if deleting the default instance."""
        instances_dir = tmp_yolo_home / "instances"
        instance_dir = instances_dir / "test"
        instance_dir.mkdir(parents=True)
        (instance_dir / "instance.json").write_text("{}")
        set_default_instance("test")

        delete_instance("test")

        assert get_default_instance() is None

    def test_delete_preserves_default_if_different(self, tmp_yolo_home):
        """Delete preserves default if deleting a different instance."""
        instances_dir = tmp_yolo_home / "instances"

        # Create two instances
        for name in ["keep", "delete"]:
            (instances_dir / name).mkdir(parents=True)
            (instances_dir / name / "instance.json").write_text("{}")

        set_default_instance("keep")
        delete_instance("delete")

        assert get_default_instance() == "keep"


class TestResolveInstance:
    """Tests for resolve_instance function."""

    def test_explicit_instance(self, instance_with_config):
        """Returns explicit instance when provided."""
        result = resolve_instance("default")
        assert result == "default"

    def test_explicit_instance_not_exists(self, tmp_yolo_home):
        """Exits when explicit instance doesn't exist."""
        with pytest.raises(SystemExit):
            resolve_instance("nonexistent")

    def test_uses_default(self, instance_with_config):
        """Uses default when no instance specified."""
        result = resolve_instance(None)
        assert result == "default"

    def test_no_default_with_instances(self, tmp_yolo_home):
        """Exits with message when no default but instances exist."""
        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "orphan").mkdir(parents=True)
        (instances_dir / "orphan" / "instance.json").write_text("{}")

        with pytest.raises(SystemExit):
            resolve_instance(None)

    def test_no_instances(self, tmp_yolo_home):
        """Exits when no instances exist."""
        with pytest.raises(SystemExit):
            resolve_instance(None)


class TestMigrateLegacyLayout:
    """Tests for maybe_migrate_legacy_layout function."""

    def test_no_migration_if_new_layout(self, tmp_yolo_home):
        """Does nothing if instances/ already exists."""
        (tmp_yolo_home / "instances").mkdir()
        (tmp_yolo_home / "config.env").write_text("OLD=config")

        maybe_migrate_legacy_layout()

        # Old config should still be there (not moved)
        assert (tmp_yolo_home / "config.env").exists()

    def test_no_migration_if_no_old_config(self, tmp_yolo_home):
        """Does nothing if old config doesn't exist."""
        maybe_migrate_legacy_layout()

        assert not (tmp_yolo_home / "instances").exists()

    def test_migrates_config_and_repo(self, tmp_yolo_home):
        """Migrates old config.env and repo/ to instances/default/."""
        # Set up old layout
        (tmp_yolo_home / "config.env").write_text("KEY=value")
        (tmp_yolo_home / "repo").mkdir()
        (tmp_yolo_home / "repo" / "Vagrantfile").touch()

        maybe_migrate_legacy_layout()

        # Check new layout
        default_dir = tmp_yolo_home / "instances" / "default"
        assert (default_dir / "config.env").read_text() == "KEY=value"
        assert (default_dir / "repo" / "Vagrantfile").exists()
        assert (default_dir / "instance.json").exists()

        # Check default was set
        assert get_default_instance() == "default"

        # Check old files were moved
        assert not (tmp_yolo_home / "config.env").exists()
        assert not (tmp_yolo_home / "repo").exists()

    def test_migrates_config_only(self, tmp_yolo_home):
        """Migrates when only config.env exists (no repo)."""
        (tmp_yolo_home / "config.env").write_text("KEY=value")

        maybe_migrate_legacy_layout()

        default_dir = tmp_yolo_home / "instances" / "default"
        assert (default_dir / "config.env").exists()
        assert not (default_dir / "repo").exists()
        assert get_default_instance() == "default"
