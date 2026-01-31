"""Instance Registry - Manages all yolo-cage instances on the host."""

from __future__ import annotations

import shutil
from pathlib import Path

from yolo_cage.host.instance import Instance


class RegistryError(Exception):
    """Base exception for registry operations."""

    pass


class NoInstancesError(RegistryError):
    """Raised when no instances exist."""

    def __init__(self) -> None:
        super().__init__(
            "No instances found. Run 'yolo-cage build' to create one."
        )


class AmbiguousInstanceError(RegistryError):
    """Raised when multiple instances exist but none is specified."""

    def __init__(self, instances: list[str]) -> None:
        instance_list = ", ".join(instances)
        super().__init__(
            f"Multiple instances exist ({instance_list}). "
            f"Use '-I <name>' or 'yolo-cage set-default <name>'."
        )
        self.instances = instances


class InstanceNotFoundError(RegistryError):
    """Raised when a specified instance doesn't exist."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Instance not found: {name}")
        self.name = name


class InstanceExistsError(RegistryError):
    """Raised when trying to create an instance that already exists."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Instance already exists: {name}")
        self.name = name


class Registry:
    """Manages all yolo-cage instances on the host.

    Attributes:
        home: yolo-cage home directory (usually ~/.yolo-cage)
    """

    def __init__(self, home: Path | None = None) -> None:
        """Initialize the registry.

        Args:
            home: yolo-cage home directory. Defaults to ~/.yolo-cage
        """
        if home is None:
            import os
            home = Path(os.environ.get("YOLO_CAGE_HOME", Path.home() / ".yolo-cage"))
        self.home = home

    @property
    def instances_dir(self) -> Path:
        """Directory containing all instances."""
        return self.home / "instances"

    @property
    def default_file(self) -> Path:
        """Path to file containing default instance name."""
        return self.home / "default"

    def list(self) -> list[Instance]:
        """List all instances.

        Returns:
            List of Instance objects, sorted by name
        """
        if not self.instances_dir.is_dir():
            return []

        instances = []
        for entry in self.instances_dir.iterdir():
            if entry.is_dir():
                instance = Instance.load(entry.name, self.home)
                if instance:
                    instances.append(instance)

        return sorted(instances, key=lambda i: i.name)

    def get(self, name: str) -> Instance | None:
        """Get an instance by name.

        Args:
            name: Instance name

        Returns:
            Instance if found, None otherwise
        """
        return Instance.load(name, self.home)

    def resolve(self, name: str | None) -> Instance:
        """Resolve to a specific instance using least-astonishment rules.

        Resolution rules:
        1. If name is specified, use that instance (error if not found)
        2. If 0 instances exist, error
        3. If 1 instance exists, use it automatically
        4. If multiple exist and default is set, use default
        5. If multiple exist and no default, error

        Args:
            name: Instance name, or None to auto-resolve

        Returns:
            The resolved Instance

        Raises:
            NoInstancesError: No instances exist
            AmbiguousInstanceError: Multiple instances exist but none specified
            InstanceNotFoundError: Specified instance doesn't exist
        """
        if name:
            instance = self.get(name)
            if not instance:
                raise InstanceNotFoundError(name)
            return instance

        instances = self.list()

        if not instances:
            raise NoInstancesError()

        if len(instances) == 1:
            return instances[0]

        # Multiple instances - check for default
        default_name = self.default
        if default_name:
            for instance in instances:
                if instance.name == default_name:
                    return instance
            # Default doesn't exist anymore, fall through to error

        # Ambiguous - user must specify
        raise AmbiguousInstanceError([i.name for i in instances])

    def create(self, name: str, repo_path: Path | None = None) -> Instance:
        """Create a new instance.

        Args:
            name: Instance name
            repo_path: Path to local dev repo, or None to clone

        Returns:
            The created Instance

        Raises:
            InstanceExistsError: Instance already exists
        """
        if self.get(name):
            raise InstanceExistsError(name)

        instance = Instance(name=name, home=self.home, repo_path=repo_path)
        instance.save()

        return instance

    def delete(self, name: str) -> None:
        """Delete an instance.

        Args:
            name: Instance name

        Raises:
            InstanceNotFoundError: Instance doesn't exist
        """
        instance = self.get(name)
        if not instance:
            raise InstanceNotFoundError(name)

        # Remove instance directory
        if instance.dir.exists():
            shutil.rmtree(instance.dir)

        # Clear default if it was this instance
        if self.default == name:
            if self.default_file.exists():
                self.default_file.unlink()

    @property
    def default(self) -> str | None:
        """Get the default instance name.

        Returns:
            Default instance name, or None if not set
        """
        if not self.default_file.exists():
            return None
        return self.default_file.read_text().strip() or None

    def set_default(self, name: str) -> None:
        """Set the default instance.

        Args:
            name: Instance name

        Raises:
            InstanceNotFoundError: Instance doesn't exist
        """
        if not self.get(name):
            raise InstanceNotFoundError(name)

        self.home.mkdir(parents=True, exist_ok=True)
        self.default_file.write_text(name + "\n")

    def migrate_legacy(self) -> bool:
        """Migrate old single-instance layout to multi-instance.

        Old layout:
            ~/.yolo-cage/config.env
            ~/.yolo-cage/repo/

        New layout:
            ~/.yolo-cage/instances/default/config.env
            ~/.yolo-cage/instances/default/repo/

        Returns:
            True if migration was performed, False if not needed
        """
        old_config = self.home / "config.env"
        old_repo = self.home / "repo"

        # Check if migration is needed
        if not old_config.exists() and not old_repo.exists():
            return False

        # Check if already migrated
        if self.instances_dir.exists() and list(self.instances_dir.iterdir()):
            return False

        # Create default instance directory
        default_dir = self.instances_dir / "default"
        default_dir.mkdir(parents=True, exist_ok=True)

        # Move config.env
        if old_config.exists():
            shutil.move(str(old_config), str(default_dir / "config.env"))

        # Move repo
        if old_repo.exists():
            shutil.move(str(old_repo), str(default_dir / "repo"))

        # Create instance.json
        instance = Instance(name="default", home=self.home, repo_path=None)
        instance.save()

        # Set as default
        self.set_default("default")

        return True
