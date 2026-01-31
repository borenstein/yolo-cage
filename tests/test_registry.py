"""Tests for Registry class."""

import pytest
from pathlib import Path

from yolo_cage.host.registry import (
    Registry,
    NoInstancesError,
    AmbiguousInstanceError,
    InstanceNotFoundError,
    InstanceExistsError,
)
from yolo_cage.host.instance import Instance


@pytest.fixture
def temp_home(tmp_path):
    """Create a temporary yolo-cage home directory."""
    return tmp_path / ".yolo-cage"


@pytest.fixture
def registry(temp_home):
    """Create a Registry with a temporary home directory."""
    return Registry(home=temp_home)


class TestRegistryList:
    """Tests for Registry.list()."""

    def test_list_empty(self, registry):
        """list() returns empty list when no instances exist."""
        assert registry.list() == []

    def test_list_returns_instances(self, registry, temp_home):
        """list() returns all instances sorted by name."""
        # Create instances
        Instance(name="zebra", home=temp_home).save()
        Instance(name="alpha", home=temp_home).save()
        Instance(name="beta", home=temp_home).save()

        instances = registry.list()
        assert len(instances) == 3
        assert [i.name for i in instances] == ["alpha", "beta", "zebra"]


class TestRegistryGet:
    """Tests for Registry.get()."""

    def test_get_nonexistent(self, registry):
        """get() returns None for nonexistent instance."""
        assert registry.get("nonexistent") is None

    def test_get_existing(self, registry, temp_home):
        """get() returns Instance when it exists."""
        Instance(name="test", home=temp_home).save()

        instance = registry.get("test")
        assert instance is not None
        assert instance.name == "test"


class TestRegistryResolve:
    """Tests for Registry.resolve()."""

    def test_resolve_explicit_name(self, registry, temp_home):
        """resolve() with explicit name returns that instance."""
        Instance(name="test", home=temp_home).save()

        instance = registry.resolve("test")
        assert instance.name == "test"

    def test_resolve_explicit_name_not_found(self, registry):
        """resolve() with nonexistent name raises InstanceNotFoundError."""
        with pytest.raises(InstanceNotFoundError) as exc_info:
            registry.resolve("nonexistent")
        assert exc_info.value.name == "nonexistent"

    def test_resolve_no_instances(self, registry):
        """resolve() with no instances raises NoInstancesError."""
        with pytest.raises(NoInstancesError):
            registry.resolve(None)

    def test_resolve_single_instance(self, registry, temp_home):
        """resolve() with single instance returns it automatically."""
        Instance(name="only-one", home=temp_home).save()

        instance = registry.resolve(None)
        assert instance.name == "only-one"

    def test_resolve_multiple_with_default(self, registry, temp_home):
        """resolve() with multiple instances uses default."""
        Instance(name="alpha", home=temp_home).save()
        Instance(name="beta", home=temp_home).save()
        registry.set_default("beta")

        instance = registry.resolve(None)
        assert instance.name == "beta"

    def test_resolve_multiple_no_default(self, registry, temp_home):
        """resolve() with multiple instances and no default raises AmbiguousInstanceError."""
        Instance(name="alpha", home=temp_home).save()
        Instance(name="beta", home=temp_home).save()

        with pytest.raises(AmbiguousInstanceError) as exc_info:
            registry.resolve(None)
        assert set(exc_info.value.instances) == {"alpha", "beta"}


class TestRegistryCreate:
    """Tests for Registry.create()."""

    def test_create_new_instance(self, registry, temp_home):
        """create() creates a new instance."""
        instance = registry.create("test")

        assert instance.name == "test"
        assert instance.exists()
        assert instance.repo_path is None

    def test_create_with_repo_path(self, registry, temp_home):
        """create() stores repo_path."""
        dev_repo = Path("/home/user/dev/yolo-cage")
        instance = registry.create("test", repo_path=dev_repo)

        assert instance.repo_path == dev_repo
        # Verify it's persisted
        loaded = registry.get("test")
        assert loaded.repo_path == dev_repo

    def test_create_existing_raises(self, registry, temp_home):
        """create() raises InstanceExistsError for existing instance."""
        Instance(name="test", home=temp_home).save()

        with pytest.raises(InstanceExistsError) as exc_info:
            registry.create("test")
        assert exc_info.value.name == "test"


class TestRegistryDelete:
    """Tests for Registry.delete()."""

    def test_delete_instance(self, registry, temp_home):
        """delete() removes instance directory."""
        Instance(name="test", home=temp_home).save()

        registry.delete("test")

        assert registry.get("test") is None

    def test_delete_nonexistent_raises(self, registry):
        """delete() raises InstanceNotFoundError for nonexistent instance."""
        with pytest.raises(InstanceNotFoundError) as exc_info:
            registry.delete("nonexistent")
        assert exc_info.value.name == "nonexistent"

    def test_delete_clears_default(self, registry, temp_home):
        """delete() clears default if deleting default instance."""
        Instance(name="test", home=temp_home).save()
        registry.set_default("test")

        registry.delete("test")

        assert registry.default is None


class TestRegistryDefault:
    """Tests for Registry.default and set_default()."""

    def test_default_none_initially(self, registry):
        """default property returns None when not set."""
        assert registry.default is None

    def test_set_default(self, registry, temp_home):
        """set_default() sets the default instance."""
        Instance(name="test", home=temp_home).save()

        registry.set_default("test")

        assert registry.default == "test"

    def test_set_default_nonexistent_raises(self, registry):
        """set_default() raises InstanceNotFoundError for nonexistent instance."""
        with pytest.raises(InstanceNotFoundError) as exc_info:
            registry.set_default("nonexistent")
        assert exc_info.value.name == "nonexistent"


class TestRegistryMigrateLegacy:
    """Tests for Registry.migrate_legacy()."""

    def test_migrate_nothing_to_migrate(self, registry):
        """migrate_legacy() returns False when nothing to migrate."""
        assert not registry.migrate_legacy()

    def test_migrate_already_migrated(self, registry, temp_home):
        """migrate_legacy() returns False when already migrated."""
        # Create an instance (new layout)
        Instance(name="existing", home=temp_home).save()

        # Create old-style files
        (temp_home / "config.env").write_text("GITHUB_PAT=test\nREPO_URL=test")

        # Should not migrate because instances already exist
        assert not registry.migrate_legacy()

    def test_migrate_config_only(self, registry, temp_home):
        """migrate_legacy() migrates config.env to default instance."""
        temp_home.mkdir(parents=True)
        old_config = temp_home / "config.env"
        old_config.write_text("GITHUB_PAT=test\nREPO_URL=test")

        result = registry.migrate_legacy()

        assert result is True
        assert not old_config.exists()

        # Check new location
        default_instance = registry.get("default")
        assert default_instance is not None
        assert default_instance.config_path.exists()
        assert default_instance.config_path.read_text() == "GITHUB_PAT=test\nREPO_URL=test"

        # Check default is set
        assert registry.default == "default"

    def test_migrate_repo_only(self, registry, temp_home):
        """migrate_legacy() migrates repo/ to default instance."""
        temp_home.mkdir(parents=True)
        old_repo = temp_home / "repo"
        old_repo.mkdir()
        (old_repo / "Vagrantfile").write_text("# test")

        result = registry.migrate_legacy()

        assert result is True
        assert not old_repo.exists()

        # Check new location
        default_instance = registry.get("default")
        assert default_instance is not None
        assert default_instance.repo_dir.is_dir()
        assert (default_instance.repo_dir / "Vagrantfile").exists()

    def test_migrate_both(self, registry, temp_home):
        """migrate_legacy() migrates both config.env and repo/."""
        temp_home.mkdir(parents=True)

        old_config = temp_home / "config.env"
        old_config.write_text("GITHUB_PAT=test\nREPO_URL=test")

        old_repo = temp_home / "repo"
        old_repo.mkdir()
        (old_repo / "Vagrantfile").write_text("# test")

        result = registry.migrate_legacy()

        assert result is True
        assert not old_config.exists()
        assert not old_repo.exists()

        default_instance = registry.get("default")
        assert default_instance.config_path.exists()
        assert default_instance.repo_dir.is_dir()
        assert registry.default == "default"
