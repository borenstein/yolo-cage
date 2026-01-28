"""Instance management for yolo-cage.

Each instance represents a separate VM with its own configuration.
Instances can use either a cloned yolo-cage repo or a local development repo.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

YOLO_CAGE_REPO = "https://github.com/borenstein/yolo-cage.git"


def get_yolo_cage_home() -> Path:
    """Get the yolo-cage home directory."""
    return Path(os.environ.get("YOLO_CAGE_HOME", Path.home() / ".yolo-cage"))


def get_instances_dir() -> Path:
    """Get the instances directory."""
    return get_yolo_cage_home() / "instances"


def list_instances() -> list[str]:
    """Return list of instance names."""
    instances_dir = get_instances_dir()
    if not instances_dir.exists():
        return []
    return sorted(
        d.name
        for d in instances_dir.iterdir()
        if d.is_dir() and (d / "instance.json").exists()
    )


def get_default_instance() -> str | None:
    """Read the default instance name from ~/.yolo-cage/default."""
    default_file = get_yolo_cage_home() / "default"
    if not default_file.exists():
        return None
    name = default_file.read_text().strip()
    # Verify the instance still exists
    if name and instance_exists(name):
        return name
    return None


def set_default_instance(name: str) -> None:
    """Write instance name to ~/.yolo-cage/default."""
    default_file = get_yolo_cage_home() / "default"
    default_file.parent.mkdir(parents=True, exist_ok=True)
    default_file.write_text(name + "\n")


def instance_exists(name: str) -> bool:
    """Check if an instance exists."""
    instance_dir = get_instances_dir() / name
    return (instance_dir / "instance.json").exists()


def get_instance_dir(name: str) -> Path:
    """Get the directory for an instance."""
    return get_instances_dir() / name


def get_instance_config(name: str) -> dict:
    """Load instance.json for an instance."""
    instance_dir = get_instance_dir(name)
    config_file = instance_dir / "instance.json"
    if not config_file.exists():
        return {}
    return json.loads(config_file.read_text())


def get_repo_dir(name: str) -> Path:
    """Return repo path - either local or cloned.

    If repo_path is set in instance.json, uses that local path.
    Otherwise, uses the cloned repo in instances/<name>/repo/.
    """
    config = get_instance_config(name)
    if config.get("repo_path"):
        return Path(config["repo_path"])
    return get_instance_dir(name) / "repo"


def get_config_path(name: str) -> Path:
    """Return the config.env path for an instance."""
    return get_instance_dir(name) / "config.env"


def detect_local_repo() -> Path | None:
    """If running from within a repo with Vagrantfile, return its path.

    This handles the case where a developer is running from their local
    checkout of yolo-cage.
    """
    # First, check if __file__ is available (normal Python execution)
    try:
        script_path = Path(__file__).resolve()
        # Go up from yolo_cage/instances.py to the repo root
        potential_repo = script_path.parent.parent
        if (potential_repo / "Vagrantfile").exists():
            return potential_repo
    except (NameError, TypeError):
        pass

    # Also check CWD in case running from repo root
    cwd = Path.cwd()
    if (cwd / "Vagrantfile").exists():
        return cwd

    return None


def create_instance(name: str, repo_path: Path | None = None) -> Path:
    """Create instance directory structure.

    If repo_path is None, clone yolo-cage into instances/<name>/repo/.
    If repo_path is provided, store it in instance.json (no clone).

    Returns the instance directory.
    """
    from .output import log_step, log_success

    instance_dir = get_instance_dir(name)
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Create instance.json
    config = {
        "repo_path": str(repo_path) if repo_path else None,
    }
    (instance_dir / "instance.json").write_text(json.dumps(config, indent=2) + "\n")

    # Clone repo if needed
    if repo_path is None:
        repo_dir = instance_dir / "repo"
        if not repo_dir.exists():
            log_step("Cloning yolo-cage repository...")
            subprocess.run(
                ["git", "clone", YOLO_CAGE_REPO, str(repo_dir)],
                check=True,
            )
            log_success("Repository cloned")

    return instance_dir


def delete_instance(name: str) -> None:
    """Delete an instance and all its data."""
    instance_dir = get_instance_dir(name)
    if instance_dir.exists():
        shutil.rmtree(instance_dir)

    # If this was the default, clear the default
    if get_default_instance() == name:
        default_file = get_yolo_cage_home() / "default"
        if default_file.exists():
            default_file.unlink()


def maybe_migrate_legacy_layout() -> None:
    """Migrate old layout to instances/default/ if needed.

    Old layout:
        ~/.yolo-cage/config.env
        ~/.yolo-cage/repo/

    New layout:
        ~/.yolo-cage/default          (contains "default")
        ~/.yolo-cage/instances/default/config.env
        ~/.yolo-cage/instances/default/repo/
        ~/.yolo-cage/instances/default/instance.json
    """
    from .output import log_step, log_success

    yolo_home = get_yolo_cage_home()
    old_config = yolo_home / "config.env"
    old_repo = yolo_home / "repo"
    instances_dir = get_instances_dir()

    # Only migrate if old layout exists and new layout doesn't
    if not old_config.exists() or instances_dir.exists():
        return

    log_step("Migrating to new instance layout...")

    default_dir = instances_dir / "default"
    default_dir.mkdir(parents=True)
    shutil.move(str(old_config), str(default_dir / "config.env"))

    if old_repo.exists():
        shutil.move(str(old_repo), str(default_dir / "repo"))

    (default_dir / "instance.json").write_text('{"repo_path": null}\n')
    set_default_instance("default")
    log_success("Migrated to instances/default/")


def resolve_instance(instance_arg: str | None) -> str:
    """Determine which instance to use. Dies if none can be determined."""
    from .output import die

    if instance_arg:
        if not instance_exists(instance_arg):
            die(f"Instance '{instance_arg}' does not exist.")
        return instance_arg

    default = get_default_instance()
    if default:
        return default

    instances = list_instances()
    if instances:
        die(f"No default instance. Use --instance=<name> or 'yolo-cage set-default <name>'.\n"
            f"Available: {', '.join(instances)}")

    die("No instances found. Run 'yolo-cage build' first.")
