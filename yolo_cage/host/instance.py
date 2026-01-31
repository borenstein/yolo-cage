"""Instance value object - A named, self-contained yolo-cage environment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yolo_cage.domain.config import Config


@dataclass
class Instance:
    """A named, self-contained yolo-cage environment.

    An Instance:
    - Has a unique name (e.g., "default", "work", "personal")
    - Has its own Configuration (PAT, repo URL, git identity)
    - Has its own Runtime (VM running MicroK8s with dispatcher, proxy, etc.)
    - Contains a copy of the System Repository (cloned or linked to local dev path)

    Attributes:
        name: Unique instance name
        home: yolo-cage home directory (usually ~/.yolo-cage)
        repo_path: Path to local dev repo, or None to use cloned repo
    """

    name: str
    home: Path
    repo_path: Path | None = None

    @property
    def dir(self) -> Path:
        """Instance directory: ~/.yolo-cage/instances/<name>/"""
        return self.home / "instances" / self.name

    @property
    def config_path(self) -> Path:
        """Path to config.env file."""
        return self.dir / "config.env"

    @property
    def repo_dir(self) -> Path:
        """System repository directory.

        Returns repo_path if set (development mode), otherwise uses cloned repo.
        """
        if self.repo_path:
            return self.repo_path
        return self.dir / "repo"

    @property
    def instance_json_path(self) -> Path:
        """Path to instance.json metadata file."""
        return self.dir / "instance.json"

    def exists(self) -> bool:
        """Check if this instance exists on disk."""
        return self.dir.is_dir()

    def config(self) -> "Config | None":
        """Load configuration for this instance.

        Returns:
            Config instance, or None if config file doesn't exist
        """
        from yolo_cage.domain.config import Config

        if not self.config_path.exists():
            return None
        return Config.load(self.config_path)

    def save(self) -> None:
        """Write instance metadata to instance.json."""
        self.dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "repo_path": str(self.repo_path) if self.repo_path else None
        }
        with open(self.instance_json_path, "w") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")

    @classmethod
    def load(cls, name: str, home: Path) -> "Instance | None":
        """Load an instance from disk.

        Args:
            name: Instance name
            home: yolo-cage home directory

        Returns:
            Instance if it exists, None otherwise
        """
        instance_dir = home / "instances" / name
        if not instance_dir.is_dir():
            return None

        instance_json = instance_dir / "instance.json"
        repo_path = None

        if instance_json.exists():
            with open(instance_json) as f:
                metadata = json.load(f)
                repo_path_str = metadata.get("repo_path")
                if repo_path_str:
                    repo_path = Path(repo_path_str)

        return cls(name=name, home=home, repo_path=repo_path)
