"""Instance management.

An instance is a named yolo-cage environment with its own config and VM.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from ..output import die, log_step, log_success

YOLO_CAGE_REPO = "https://github.com/borenstein/yolo-cage.git"


def get_home() -> Path:
    """Get yolo-cage home directory (~/.yolo-cage)."""
    return Path(os.environ.get("YOLO_CAGE_HOME", Path.home() / ".yolo-cage"))


def get_instances_dir() -> Path:
    """Get instances directory."""
    return get_home() / "instances"


def list_instances() -> list[str]:
    """Return sorted list of instance names."""
    instances_dir = get_instances_dir()
    if not instances_dir.exists():
        return []
    return sorted(
        d.name for d in instances_dir.iterdir()
        if d.is_dir() and (d / "instance.json").exists()
    )


def instance_exists(name: str) -> bool:
    """Check if instance exists."""
    return (get_instances_dir() / name / "instance.json").exists()


def get_instance_dir(name: str) -> Path:
    """Get instance directory."""
    return get_instances_dir() / name


def get_config_path(name: str) -> Path:
    """Get config.env path for instance."""
    return get_instance_dir(name) / "config.env"


def get_repo_dir(name: str) -> Path:
    """Get repo directory for instance.

    Returns local dev path if configured, otherwise cloned repo.
    """
    config = _load_instance_json(name)
    if config.get("repo_path"):
        return Path(config["repo_path"])
    return get_instance_dir(name) / "repo"


def _load_instance_json(name: str) -> dict:
    """Load instance.json metadata."""
    path = get_instance_dir(name) / "instance.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save_instance_json(name: str, repo_path: Path | None) -> None:
    """Save instance.json metadata."""
    instance_dir = get_instance_dir(name)
    instance_dir.mkdir(parents=True, exist_ok=True)
    data = {"repo_path": str(repo_path) if repo_path else None}
    (instance_dir / "instance.json").write_text(json.dumps(data, indent=2) + "\n")


def get_default() -> str | None:
    """Get default instance name, or None."""
    default_file = get_home() / "default"
    if not default_file.exists():
        return None
    name = default_file.read_text().strip()
    return name if name and instance_exists(name) else None


def set_default(name: str) -> None:
    """Set default instance."""
    if not instance_exists(name):
        die(f"Instance not found: {name}")
    default_file = get_home() / "default"
    default_file.parent.mkdir(parents=True, exist_ok=True)
    default_file.write_text(name + "\n")


def resolve(name: str | None) -> str:
    """Resolve instance name using least-astonishment rules.

    1. If name given, use it (error if not found)
    2. If only one instance exists, use it
    3. If default is set, use it
    4. Otherwise, error with guidance
    """
    if name:
        if not instance_exists(name):
            die(f"Instance not found: {name}")
        return name

    instances = list_instances()

    if not instances:
        die("No instances found. Run 'yolo-cage build' first.")

    if len(instances) == 1:
        return instances[0]

    default = get_default()
    if default:
        return default

    die(f"Multiple instances exist ({', '.join(instances)}). "
        f"Use -I <name> or 'yolo-cage set-default <name>'.")


def create(name: str, repo_path: Path | None = None) -> Path:
    """Create a new instance. Returns instance directory."""
    if instance_exists(name):
        die(f"Instance already exists: {name}")

    _save_instance_json(name, repo_path)

    if repo_path is None:
        repo_dir = get_instance_dir(name) / "repo"
        if not repo_dir.exists():
            log_step("Cloning yolo-cage repository...")
            subprocess.run(["git", "clone", YOLO_CAGE_REPO, str(repo_dir)], check=True)
            log_success("Repository cloned")

    return get_instance_dir(name)


def delete(name: str) -> None:
    """Delete an instance."""
    if not instance_exists(name):
        die(f"Instance not found: {name}")

    instance_dir = get_instance_dir(name)
    if instance_dir.exists():
        shutil.rmtree(instance_dir)

    if get_default() == name:
        default_file = get_home() / "default"
        if default_file.exists():
            default_file.unlink()


def detect_dev_repo() -> Path | None:
    """Detect if running from a development repo."""
    try:
        # Go up from yolo_cage/instances.py to repo root
        module_path = Path(__file__).resolve()
        repo_root = module_path.parent.parent
        if (repo_root / "Vagrantfile").exists():
            return repo_root
    except Exception:
        pass
    return None


def migrate_legacy() -> bool:
    """Migrate old single-instance layout to multi-instance.

    Old: ~/.yolo-cage/config.env, ~/.yolo-cage/repo/
    New: ~/.yolo-cage/instances/default/...

    Returns True if migration was performed.
    """
    home = get_home()
    old_config = home / "config.env"
    old_repo = home / "repo"

    if not old_config.exists() and not old_repo.exists():
        return False

    if get_instances_dir().exists() and list_instances():
        return False

    log_step("Migrating to multi-instance layout...")

    default_dir = get_instances_dir() / "default"
    default_dir.mkdir(parents=True, exist_ok=True)

    if old_config.exists():
        shutil.move(str(old_config), str(default_dir / "config.env"))
    if old_repo.exists():
        shutil.move(str(old_repo), str(default_dir / "repo"))

    _save_instance_json("default", None)
    set_default("default")

    log_success("Migrated to instances/default/")
    return True
