"""Tests for Registry class."""

import json
import pytest
from pathlib import Path

from yolo_cage.registry import Registry
from yolo_cage.errors import InstanceNotFound, InstanceExists, NoDefaultInstance


class TestRegistryList:
    """Tests for Registry.list()."""

    def test_empty_when_no_instances_dir(self, tmp_yolo_home):
        registry = Registry()
        assert registry.list() == []

    def test_empty_when_instances_dir_empty(self, tmp_yolo_home):
        (tmp_yolo_home / "instances").mkdir()
        registry = Registry()
        assert registry.list() == []

    def test_lists_valid_instances(self, tmp_yolo_home):
        instances_dir = tmp_yolo_home / "instances"
        (instances_dir / "foo").mkdir(parents=True)
        (instances_dir / "foo" / "instance.json").write_text("{}")
        (instances_dir / "invalid").mkdir()  # No instance.json

        registry = Registry()
        instances = registry.list()
        assert len(instances) == 1
        assert instances[0].name == "foo"

    def test_sorted_alphabetically(self, tmp_yolo_home):
        instances_dir = tmp_yolo_home / "instances"
        for name in ["zebra", "alpha", "middle"]:
            (instances_dir / name).mkdir(parents=True)
            (instances_dir / name / "instance.json").write_text("{}")

        registry = Registry()
        names = [i.name for i in registry.list()]
        assert names == ["alpha", "middle", "zebra"]


class TestRegistryGet:
    """Tests for Registry.get()."""

    def test_returns_none_if_missing(self, tmp_yolo_home):
        registry = Registry()
        assert registry.get("nonexistent") is None

    def test_returns_instance(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text('{"repo_path": null}')

        registry = Registry()
        instance = registry.get("test")
        assert instance is not None
        assert instance.name == "test"


class TestRegistryDefault:
    """Tests for Registry default management."""

    def test_default_name_none_when_no_file(self, tmp_yolo_home):
        registry = Registry()
        assert registry.default_name is None

    def test_default_name_none_when_instance_deleted(self, tmp_yolo_home):
        (tmp_yolo_home / "default").write_text("deleted\n")
        registry = Registry()
        assert registry.default_name is None

    def test_set_and_get_default(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")

        registry = Registry()
        registry.set_default("test")
        assert registry.default_name == "test"

    def test_set_default_nonexistent_raises(self, tmp_yolo_home):
        registry = Registry()
        with pytest.raises(InstanceNotFound):
            registry.set_default("nonexistent")


class TestRegistryResolve:
    """Tests for Registry.resolve()."""

    def test_explicit_instance(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")

        registry = Registry()
        instance = registry.resolve("test")
        assert instance.name == "test"

    def test_explicit_nonexistent_raises(self, tmp_yolo_home):
        registry = Registry()
        with pytest.raises(InstanceNotFound):
            registry.resolve("nonexistent")

    def test_uses_default(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "mydefault"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")
        (tmp_yolo_home / "default").write_text("mydefault\n")

        registry = Registry()
        instance = registry.resolve(None)
        assert instance.name == "mydefault"

    def test_no_default_with_instances_raises(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "orphan"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")

        registry = Registry()
        with pytest.raises(NoDefaultInstance):
            registry.resolve(None)

    def test_no_instances_raises(self, tmp_yolo_home):
        registry = Registry()
        with pytest.raises(InstanceNotFound):
            registry.resolve(None)


class TestRegistryCreate:
    """Tests for Registry.create()."""

    def test_create_with_local_repo(self, tmp_yolo_home, tmp_path):
        local_repo = tmp_path / "my-repo"
        local_repo.mkdir()

        registry = Registry()
        instance = registry.create("test", repo_path=local_repo)

        assert instance.name == "test"
        assert instance.exists()
        assert instance._repo_path == local_repo

    def test_create_existing_raises(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")

        registry = Registry()
        with pytest.raises(InstanceExists):
            registry.create("test")


class TestRegistryDelete:
    """Tests for Registry.delete()."""

    def test_delete_removes_directory(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")

        registry = Registry()
        registry.delete("test")
        assert not inst_dir.exists()

    def test_delete_clears_default(self, tmp_yolo_home):
        inst_dir = tmp_yolo_home / "instances" / "test"
        inst_dir.mkdir(parents=True)
        (inst_dir / "instance.json").write_text("{}")
        (tmp_yolo_home / "default").write_text("test\n")

        registry = Registry()
        registry.delete("test")
        assert registry.default_name is None

    def test_delete_preserves_other_default(self, tmp_yolo_home):
        for name in ["keep", "delete"]:
            inst_dir = tmp_yolo_home / "instances" / name
            inst_dir.mkdir(parents=True)
            (inst_dir / "instance.json").write_text("{}")
        (tmp_yolo_home / "default").write_text("keep\n")

        registry = Registry()
        registry.delete("delete")
        assert registry.default_name == "keep"


class TestRegistryMigration:
    """Tests for legacy layout migration."""

    def test_no_migration_if_new_layout(self, tmp_yolo_home):
        (tmp_yolo_home / "instances").mkdir()
        (tmp_yolo_home / "config.env").write_text("OLD=config")

        registry = Registry()
        result = registry.migrate_if_needed()

        assert result is False
        assert (tmp_yolo_home / "config.env").exists()

    def test_no_migration_if_no_old_config(self, tmp_yolo_home):
        registry = Registry()
        result = registry.migrate_if_needed()

        assert result is False
        assert not (tmp_yolo_home / "instances").exists()

    def test_migrates_config_and_repo(self, tmp_yolo_home):
        (tmp_yolo_home / "config.env").write_text("KEY=value")
        (tmp_yolo_home / "repo").mkdir()
        (tmp_yolo_home / "repo" / "Vagrantfile").touch()

        registry = Registry()
        result = registry.migrate_if_needed()

        assert result is True
        default_dir = tmp_yolo_home / "instances" / "default"
        assert (default_dir / "config.env").read_text() == "KEY=value"
        assert (default_dir / "repo" / "Vagrantfile").exists()
        assert registry.default_name == "default"
        assert not (tmp_yolo_home / "config.env").exists()
