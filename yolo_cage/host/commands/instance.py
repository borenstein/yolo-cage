"""Instance management commands."""

import argparse

from .. import instances
from ...output import log_success


def cmd_instances(args: argparse.Namespace) -> None:
    """List all instances."""
    instances.migrate_legacy()
    names = instances.list_instances()
    default = instances.get_default()

    if not names:
        print("No instances found.")
        print("Run 'yolo-cage build --interactive' to create one.")
        return

    print("Instances:")
    for name in names:
        marker = " (default)" if name == default else ""
        repo_dir = instances.get_repo_dir(name)
        repo_type = "dev" if instances._load_instance_json(name).get("repo_path") else "cloned"
        print(f"  {name}{marker} [{repo_type}]")


def cmd_set_default(args: argparse.Namespace) -> None:
    """Set the default instance."""
    instances.migrate_legacy()
    instances.set_default(args.name)
    log_success(f"Default set to: {args.name}")


def cmd_delete_instance(args: argparse.Namespace) -> None:
    """Delete an instance."""
    import subprocess
    from ...output import die, log_step

    instances.migrate_legacy()
    name = args.name

    if not instances.instance_exists(name):
        die(f"Instance not found: {name}")

    if not args.force:
        print(f"This will delete instance '{name}' and all its data.")
        confirm = input("Continue? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Aborted.")
            return

    repo_dir = instances.get_repo_dir(name)
    if (repo_dir / ".vagrant").exists():
        log_step("Destroying VM...")
        subprocess.run(["vagrant", "destroy", "-f"], cwd=repo_dir)

    instances.delete(name)
    log_success(f"Instance '{name}' deleted")
