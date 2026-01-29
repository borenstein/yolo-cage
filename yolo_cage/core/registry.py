"""Registry - manages the collection of yolo-cage instances."""

import os
import shutil
from pathlib import Path

from ..errors import InstanceNotFound, InstanceExists, NoDefaultInstance
from .instance import Instance


class Registry:
    """Manages yolo-cage instances."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or self._default_base_dir()

    @staticmethod
    def _default_base_dir() -> Path:
        return Path(os.environ.get("YOLO_CAGE_HOME", Path.home() / ".yolo-cage"))

    def list(self) -> list[Instance]:
        """List all instances."""
        instances_dir = self.base_dir / "instances"
        if not instances_dir.exists():
            return []

        instances = []
        for d in sorted(instances_dir.iterdir()):
            if d.is_dir():
                instance = Instance.load(d.name, self.base_dir)
                if instance:
                    instances.append(instance)
        return instances

    def get(self, name: str) -> Instance | None:
        """Get instance by name. Returns None if not found."""
        return Instance.load(name, self.base_dir)

    @property
    def default_name(self) -> str | None:
        """Name of the default instance, or None."""
        default_file = self.base_dir / "default"
        if not default_file.exists():
            return None

        name = default_file.read_text().strip()
        if name and self.get(name):
            return name
        return None

    def set_default(self, name: str) -> None:
        """Set the default instance. Raises InstanceNotFound if invalid."""
        if not self.get(name):
            raise InstanceNotFound(f"Instance '{name}' does not exist.")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "default").write_text(name + "\n")

    def resolve(self, name: str | None) -> Instance:
        """Resolve instance by name or default. Raises if not found."""
        if name:
            instance = self.get(name)
            if not instance:
                raise InstanceNotFound(f"Instance '{name}' does not exist.")
            return instance

        if self.default_name:
            return self.get(self.default_name)

        instances = self.list()
        if instances:
            names = [i.name for i in instances]
            raise NoDefaultInstance(
                f"No default instance. Use -I <name> or 'yolo-cage set-default <name>'.\n"
                f"Available: {', '.join(names)}"
            )

        raise InstanceNotFound("No instances found. Run 'yolo-cage build' first.")

    def create(self, name: str, repo_path: Path | None = None) -> Instance:
        """Create a new instance. Raises InstanceExists if name taken."""
        if self.get(name):
            raise InstanceExists(f"Instance '{name}' already exists.")

        instance = Instance(name, self.base_dir, repo_path)
        instance.save()
        return instance

    def delete(self, name: str) -> None:
        """Delete an instance and clear default if needed."""
        instance = self.get(name)
        if not instance:
            return

        if instance.dir.exists():
            shutil.rmtree(instance.dir)

        if self.default_name == name:
            default_file = self.base_dir / "default"
            if default_file.exists():
                default_file.unlink()

    def detect_local_repo(self) -> Path | None:
        """Detect if running from a local yolo-cage checkout."""
        try:
            script_path = Path(__file__).resolve()
            # Go up from core/registry.py -> core -> yolo_cage -> repo root
            potential = script_path.parent.parent.parent
            if (potential / "Vagrantfile").exists():
                return potential
        except (NameError, TypeError):
            pass

        if (Path.cwd() / "Vagrantfile").exists():
            return Path.cwd()
        return None

    def is_repo_in_use(self, repo_path: Path) -> bool:
        """Check if a local repo is already used by an instance."""
        for instance in self.list():
            if instance._repo_path and instance._repo_path == repo_path:
                return True
        return False

    def migrate_if_needed(self) -> bool:
        """Migrate legacy layout if present. Returns True if migrated."""
        old_config = self.base_dir / "config.env"
        instances_dir = self.base_dir / "instances"

        if not old_config.exists() or instances_dir.exists():
            return False

        default_dir = instances_dir / "default"
        default_dir.mkdir(parents=True)

        shutil.move(str(old_config), str(default_dir / "config.env"))

        old_repo = self.base_dir / "repo"
        if old_repo.exists():
            shutil.move(str(old_repo), str(default_dir / "repo"))

        (default_dir / "instance.json").write_text('{"repo_path": null}\n')
        (self.base_dir / "default").write_text("default\n")

        return True
