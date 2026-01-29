"""Application services - use case orchestration."""

import subprocess
from pathlib import Path

from .config import Config
from .errors import ConfigError, GitHubAccessError, PrerequisitesMissing
from .github import validate_github_repo
from .instance import Instance
from .prerequisites import check_dependencies
from .registry import Registry


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
    Raises on any failure.
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


def upgrade_cli(target_path: Path) -> None:
    """Download and install latest CLI binary."""
    import os
    import tempfile
    import urllib.request

    cli_url = "https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage"

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        try:
            urllib.request.urlretrieve(cli_url, tmp.name)
            os.chmod(tmp.name, 0o755)
            subprocess.run(["sudo", "cp", tmp.name, str(target_path)], check=True)
        finally:
            os.unlink(tmp.name)


def upgrade_repo(instance: Instance) -> bool:
    """Update instance repo from origin. Returns True if updated."""
    if instance._repo_path:
        return False  # Local repo, skip

    if not instance.repo_dir.exists():
        return False

    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=instance.repo_dir,
        capture_output=True,
    )
    subprocess.run(
        ["git", "reset", "--hard", "origin/main"],
        cwd=instance.repo_dir,
        capture_output=True,
    )
    return True


def rebuild_vm(instance: Instance) -> None:
    """Destroy and rebuild VM, then sync config."""
    instance.vm.destroy()
    instance.vm.start()
    sync_config(instance)


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


def clone_repo(target_dir: Path) -> None:
    """Clone yolo-cage repository to target directory."""
    if target_dir.exists():
        return
    subprocess.run(
        ["git", "clone", YOLO_CAGE_REPO, str(target_dir)],
        check=True,
    )


def validate_config(config: Config) -> None:
    """Validate GitHub access. Raises GitHubAccessError on failure."""
    valid, message = validate_github_repo(config.repo_url, config.github_pat)
    if not valid:
        raise GitHubAccessError(message)
