"""Build workflow for yolo-cage instances."""

import subprocess
from pathlib import Path

from ..core import Config, Instance, Registry
from ..errors import ConfigError, PrerequisitesMissing
from .github import validate_config
from .prerequisites import check_dependencies


YOLO_CAGE_REPO = "https://github.com/borenstein/yolo-cage.git"


def build(
    registry: Registry,
    name: str | None,
    config: Config | None,
    keep_running: bool,
) -> Instance:
    """
    Build a new yolo-cage instance.

    Orchestrates: prerequisites, instance creation, repo cloning, VM setup.
    Returns the created instance.
    """
    missing = check_dependencies()
    if missing:
        raise PrerequisitesMissing(missing)

    name = name or "default"

    local_repo = registry.detect_local_repo()
    use_local = local_repo and not registry.is_repo_in_use(local_repo)
    repo_path = local_repo if use_local else None

    instance = registry.create(name, repo_path)

    if not registry.default_name:
        registry.set_default(name)

    if config:
        config.save(instance.config_path)
    elif not instance.config_path.exists():
        raise ConfigError("No config provided. Use --interactive or --config-file.")

    loaded_config = Config.load(instance.config_path)
    if not loaded_config:
        raise ConfigError(f"Invalid config at {instance.config_path}")
    validate_config(loaded_config)

    if repo_path is None:
        clone_repo(instance.dir / "repo")

    if (instance.repo_dir / ".vagrant").exists():
        instance.vm.destroy()

    instance.vm.start()
    sync_config(instance)

    if not keep_running:
        instance.vm.stop()

    return instance


def clone_repo(target_dir: Path) -> None:
    """Clone yolo-cage repository to target directory."""
    if target_dir.exists():
        return
    subprocess.run(
        ["git", "clone", YOLO_CAGE_REPO, str(target_dir)],
        check=True,
    )


def sync_config(instance: Instance) -> None:
    """Sync config.env to VM and apply it."""
    if not instance.config_path.exists():
        raise ConfigError("No config found. Run 'yolo-cage configure' first.")

    instance.vm.ssh("mkdir -p ~/.yolo-cage")

    subprocess.run(
        ["vagrant", "ssh", "-c", "cat > ~/.yolo-cage/config.env"],
        cwd=instance.repo_dir,
        input=instance.config_path.read_text(),
        text=True,
        check=True,
    )

    instance.vm.ssh("yolo-cage-configure")
