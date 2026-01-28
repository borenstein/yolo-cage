"""Command-line interface for yolo-cage."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from . import __version__
from .config import Config
from .output import die, log_step, log_success, log_error, YELLOW, NC
from .prerequisites import check_prerequisites
from .registry import Registry


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="yolo-cage",
        description="Sandboxed Claude Code agents",
    )
    parser.add_argument("--version", "-v", action="version", version=f"yolo-cage {__version__}")
    parser.add_argument("-I", "--instance", metavar="NAME", help="Target instance")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # version
    sub.add_parser("version", help="Show version")

    # build
    p = sub.add_parser("build", help="Set up yolo-cage (clone repo, build VM)")
    p.add_argument("--config-file", metavar="FILE", help="Path to config.env")
    p.add_argument("--interactive", action="store_true", help="Prompt for config")
    p.add_argument("--up", action="store_true", help="Keep VM running after build")
    p.add_argument("-I", "--instance", metavar="NAME", help="Instance name")

    # instances
    sub.add_parser("instances", help="List all instances")

    # set-default
    p = sub.add_parser("set-default", help="Set the default instance")
    p.add_argument("name", help="Instance name")

    # upgrade
    p = sub.add_parser("upgrade", help="Upgrade to latest version")
    p.add_argument("--rebuild", action="store_true", help="Rebuild VM after upgrade")

    # up
    p = sub.add_parser("up", help="Start the VM", aliases=["start"])
    p.add_argument("--ram", metavar="SIZE", help="RAM size (not implemented)")

    # down
    sub.add_parser("down", help="Stop the VM", aliases=["stop", "halt"])

    # destroy
    sub.add_parser("destroy", help="Destroy the VM")

    # status
    sub.add_parser("status", help="Show VM and pod status")

    # configure
    p = sub.add_parser("configure", help="Update configuration")
    p.add_argument("--interactive", "-i", action="store_true", help="Prompt for config")

    # create
    p = sub.add_parser("create", help="Create a sandbox pod")
    p.add_argument("branch", help="Git branch name")

    # attach
    p = sub.add_parser("attach", help="Start interactive Claude session")
    p.add_argument("branch", help="Git branch name")

    # shell
    p = sub.add_parser("shell", help="Open shell in sandbox", aliases=["sh"])
    p.add_argument("branch", help="Git branch name")

    # list
    sub.add_parser("list", help="List sandbox pods", aliases=["ls"])

    # delete
    p = sub.add_parser("delete", help="Delete a sandbox pod", aliases=["rm"])
    p.add_argument("branch", help="Git branch name")
    p.add_argument("--clean", action="store_true", help="Delete workspace files")

    # logs
    p = sub.add_parser("logs", help="Tail pod logs")
    p.add_argument("branch", help="Git branch name")

    # port-forward
    p = sub.add_parser("port-forward", help="Forward port from sandbox")
    p.add_argument("branch", help="Git branch name")
    p.add_argument("port", help="PORT or LOCAL:POD")
    p.add_argument("--bind", default="127.0.0.1", metavar="ADDR", help="Bind address")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "version": cmd_version,
        "build": cmd_build,
        "instances": cmd_instances,
        "set-default": cmd_set_default,
        "upgrade": cmd_upgrade,
        "up": cmd_up,
        "start": cmd_up,
        "down": cmd_down,
        "stop": cmd_down,
        "halt": cmd_down,
        "destroy": cmd_destroy,
        "status": cmd_status,
        "configure": cmd_configure,
        "create": cmd_create,
        "attach": cmd_attach,
        "shell": cmd_shell,
        "sh": cmd_shell,
        "list": cmd_list,
        "ls": cmd_list,
        "delete": cmd_delete,
        "rm": cmd_delete,
        "logs": cmd_logs,
        "port-forward": cmd_port_forward,
    }

    commands[args.command](args)


# --- Commands ---

def cmd_version(args: argparse.Namespace) -> None:
    print(f"yolo-cage {__version__}")


def cmd_build(args: argparse.Namespace) -> None:
    check_prerequisites()

    if sys.platform == "darwin":
        print(f"\n{YELLOW}Note: Apple Silicon support is experimental.{NC}\n")

    registry = Registry()
    instances = registry.list()

    # Determine instance name
    if instances and not args.instance:
        names = [i.name for i in instances]
        die(f"Instance exists. Use --instance=<name>.\nExisting: {', '.join(names)}")

    name = args.instance or "default"
    if registry.get(name):
        die(f"Instance '{name}' already exists.")

    # Choose repo path
    local_repo = registry.detect_local_repo()
    if local_repo and not registry.is_repo_in_use(local_repo):
        log_step(f"Using local repository: {local_repo}")
        repo_path = local_repo
    else:
        if local_repo:
            log_step("Local repo already in use, cloning instead...")
        repo_path = None

    instance = registry.create(name, repo_path)

    if not registry.default_name:
        registry.set_default(name)
        log_success(f"Instance '{name}' set as default")

    # Configuration
    if args.config_file:
        src = Path(args.config_file)
        if not src.exists():
            die(f"Config file not found: {src}")
        shutil.copy(src, instance.config_path)
        log_success(f"Config copied to {instance.config_path}")
    elif args.interactive:
        config = Config.prompt()
        config.save(instance.config_path)
        log_success(f"Config written to {instance.config_path}")
    elif instance.config_path.exists():
        log_success(f"Using existing config: {instance.config_path}")
    else:
        die("No config. Use --interactive or --config-file.")

    # Build VM
    vm = instance.vm
    if (instance.repo_dir / ".vagrant").exists():
        log_step("Destroying existing VM...")
        vm.destroy()

    log_step("Building VM (this may take a while)...")
    vm.start()
    vm.sync_config(instance.config_path)

    if args.up:
        log_success("VM built and running!")
        print("Create a sandbox:  yolo-cage create <branch>")
        print("List sandboxes:    yolo-cage list")
    else:
        vm.stop()
        log_success("VM built successfully!")
        print("Run 'yolo-cage up' to start the VM.")


def cmd_instances(args: argparse.Namespace) -> None:
    registry = Registry()
    instances = registry.list()

    if not instances:
        print("No instances found.")
        print("\nRun 'yolo-cage build --interactive --up' to create one.")
        return

    print("Instances:")
    for instance in instances:
        marker = " *" if instance.name == registry.default_name else ""
        print(f"  {instance.name}{marker}")
    print("\n* = default instance")


def cmd_set_default(args: argparse.Namespace) -> None:
    registry = Registry()
    instances = registry.list()

    if not registry.get(args.name):
        if instances:
            names = [i.name for i in instances]
            die(f"Instance '{args.name}' does not exist.\nAvailable: {', '.join(names)}")
        die(f"Instance '{args.name}' does not exist. No instances found.")

    registry.set_default(args.name)
    log_success(f"Default instance set to '{args.name}'")


def cmd_upgrade(args: argparse.Namespace) -> None:
    registry = Registry()
    instance_name = args.instance or registry.default_name

    # Download CLI
    cli_url = "https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage"
    cli_path = "/usr/local/bin/yolo-cage"

    log_step("Downloading latest CLI...")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        try:
            urllib.request.urlretrieve(cli_url, tmp.name)
            os.chmod(tmp.name, 0o755)
            subprocess.run(["sudo", "cp", tmp.name, cli_path], check=True)
            log_success("CLI updated")
        finally:
            os.unlink(tmp.name)

    if not instance_name:
        return

    instance = registry.get(instance_name)
    if not instance:
        return

    # Update repo (skip if local)
    if not instance._repo_path:
        if instance.repo_dir.exists():
            log_step(f"Updating repository for '{instance_name}'...")
            subprocess.run(["git", "fetch", "origin"], cwd=instance.repo_dir, capture_output=True)
            result = subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                cwd=instance.repo_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                log_success("Repository updated")
            else:
                log_error(f"Failed: {result.stderr}")
    else:
        print(f"Skipping repo update for '{instance_name}' (local repo)")

    if args.rebuild:
        log_step(f"Rebuilding VM for '{instance_name}'...")
        instance.vm.destroy()
        instance.vm.start()
        instance.vm.sync_config(instance.config_path)
        log_success("VM rebuilt")
    else:
        print("\nRun 'yolo-cage upgrade --rebuild' to update the VM.")


def cmd_up(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_exists()

    if hasattr(args, 'ram') and args.ram:
        print("Note: --ram is not yet implemented.")

    log_step(f"Starting VM for '{instance.name}'...")
    instance.vm.start()
    log_success("VM is running")
    print("\nCreate a sandbox:  yolo-cage create <branch>")
    print("List sandboxes:    yolo-cage list")


def cmd_down(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_exists()

    log_step(f"Stopping VM for '{instance.name}'...")
    instance.vm.stop()
    log_success("VM stopped")


def cmd_destroy(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_exists()

    print(f"This will destroy the VM for '{instance.name}' and all data inside it.")
    print(f"Your config in {instance.config_path} will be preserved.\n")
    confirm = input("Continue? [y/N] ").strip().lower()

    if confirm not in ("y", "yes"):
        print("Aborted.")
        return

    log_step("Destroying VM...")
    instance.vm.destroy()
    log_success("VM destroyed")


def cmd_status(args: argparse.Namespace) -> None:
    registry = Registry()
    instances = registry.list()

    if not instances:
        print("No instances found.\nRun 'yolo-cage build --interactive --up' to get started.")
        return

    targets = [registry.resolve(args.instance)] if args.instance else instances

    for instance in targets:
        marker = " *" if instance.name == registry.default_name else ""
        print(f"Instance: {instance.name}{marker}")
        print(f"  Repository: {instance.repo_dir}")
        print(f"  Config: {instance.config_path}")

        status = instance.vm.status
        print(f"  VM status: {status}")

        if status == "running":
            print("\n  Pods:")
            instance.vm.ssh("yolo-cage-inner list")
        print()


def cmd_configure(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)

    if args.interactive:
        config = Config.prompt()
        config.save(instance.config_path)
        log_success(f"Config written to {instance.config_path}")
    else:
        config = instance.config
        if not config:
            die(f"No config at {instance.config_path}. Use --interactive.")
        config.validate()

    if instance.vm.status == "running":
        instance.vm.sync_config(instance.config_path)
    else:
        log_success(f"Config saved to {instance.config_path}")
        if instance.repo_dir.exists():
            print("VM not running. Config will apply on next 'yolo-cage up'.")


def cmd_create(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_running()

    config = instance.config
    if not config:
        die("Missing configuration. Run 'yolo-cage configure'.")
    config.validate()

    instance.vm.ssh(f"yolo-cage-inner create '{args.branch}'")

    # Show hint for attaching
    prefix = f"-I {instance.name} " if instance.name != registry.default_name else ""
    print(f"Run: yolo-cage {prefix}attach {args.branch}")


def cmd_attach(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_running()
    instance.vm.ssh(f"yolo-cage-inner attach '{args.branch}'", interactive=True)


def cmd_shell(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_running()
    instance.vm.ssh(f"yolo-cage-inner shell '{args.branch}'", interactive=True)


def cmd_list(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_running()
    instance.vm.ssh("yolo-cage-inner list")


def cmd_delete(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_running()

    cmd = f"yolo-cage-inner delete '{args.branch}'"
    if args.clean:
        cmd += " --clean"
    instance.vm.ssh(cmd)


def cmd_logs(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_running()
    instance.vm.ssh(f"yolo-cage-inner logs '{args.branch}'")


def cmd_port_forward(args: argparse.Namespace) -> None:
    registry = Registry()
    instance = registry.resolve(args.instance)
    instance.vm.require_running()

    if ":" in args.port:
        local_port, pod_port = args.port.split(":", 1)
    else:
        local_port = pod_port = args.port

    try:
        int(local_port)
        int(pod_port)
    except ValueError:
        die(f"Invalid port specification: {args.port}")

    pod_name = f"yolo-cage-{args.branch}"
    print(f"Forwarding {args.bind}:{local_port} -> {pod_name}:{pod_port}")
    print("Press Ctrl+C to stop\n")

    kubectl_cmd = f"kubectl port-forward -n yolo-cage pod/{pod_name} {local_port}:{pod_port}"
    ssh_cmd = [
        "vagrant", "ssh", "--", "-L",
        f"{args.bind}:{local_port}:localhost:{local_port}",
        kubectl_cmd,
    ]

    try:
        subprocess.call(ssh_cmd, cwd=instance.repo_dir)
    except KeyboardInterrupt:
        print("\nPort forwarding stopped.")


if __name__ == "__main__":
    main()
