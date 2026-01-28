"""Instance - a named yolo-cage environment."""

import json
from pathlib import Path

from .config import Config
from .vm import VM


class Instance:
    """A named yolo-cage environment with configuration and VM."""

    def __init__(self, name: str, base_dir: Path, repo_path: Path | None = None):
        self.name = name
        self._base_dir = base_dir
        self._repo_path = repo_path  # None means cloned repo

    @property
    def dir(self) -> Path:
        """Instance directory: ~/.yolo-cage/instances/<name>/"""
        return self._base_dir / "instances" / self.name

    @property
    def config_path(self) -> Path:
        """Path to config.env file."""
        return self.dir / "config.env"

    @property
    def repo_dir(self) -> Path:
        """Path to yolo-cage repo (local or cloned)."""
        if self._repo_path:
            return self._repo_path
        return self.dir / "repo"

    @property
    def config(self) -> Config | None:
        """Load configuration. Returns None if not configured."""
        return Config.load(self.config_path)

    @property
    def vm(self) -> VM:
        """Get VM for this instance."""
        return VM(self.repo_dir)

    def exists(self) -> bool:
        """Check if instance metadata exists."""
        return (self.dir / "instance.json").exists()

    def save(self) -> None:
        """Write instance metadata."""
        self.dir.mkdir(parents=True, exist_ok=True)
        metadata = {"repo_path": str(self._repo_path) if self._repo_path else None}
        (self.dir / "instance.json").write_text(json.dumps(metadata, indent=2) + "\n")

    @classmethod
    def load(cls, name: str, base_dir: Path) -> "Instance | None":
        """Load existing instance. Returns None if not found."""
        metadata_path = base_dir / "instances" / name / "instance.json"
        if not metadata_path.exists():
            return None

        metadata = json.loads(metadata_path.read_text())
        repo_path = Path(metadata["repo_path"]) if metadata.get("repo_path") else None
        return cls(name, base_dir, repo_path)
