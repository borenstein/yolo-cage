"""Command-line interface for yolo-cage."""

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import services
from .config import Config
from .errors import YoloCageError, PrerequisitesMissing
from .github import validate_github_repo
from .output import die, log_step, log_success, YELLOW, NC
from .prerequisites import format_install_instructions
from .registry import Registry


COMMANDS = {}


def command(name, requires=None, aliases=()):
    """Register a command with its requirements."""
    def decorator(fn):
        COMMANDS[name] = (fn, requires)
        for alias in aliases:
            COMMANDS[alias] = (fn, requires)
        return fn
    return decorator


def main() -> None:
    """Main entry point."""
    args = parse_args()
    if not args.command:
        args.parser.print_help()
        sys.exit(0)

    handler, requires = COMMANDS[args.command]
    registry = Registry()

    if registry.migrate_if_needed():
        log_success("Migrated to instances/default/")

    instance = None
    try:
        if requires:
            instance = registry.resolve(args.instance)
            if requires == "exists":
                instance.vm.require_exists()
            elif requires == "running":
                instance.vm.require_running()

        handler(args, registry, instance)

    except PrerequisitesMissing as e:
        print(format_install_instructions(e.missing))
        sys.exit(1)
    except YoloCageError as e:
        die(str(e))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(prog="yolo-cage", description="Sandboxed Claude Code agents")
    p.add_argument("--version", "-v", action="version", version=f"yolo-cage {__version__}")
    p.add_argument("-I", "--instance", metavar="NAME", help="Target instance")

    sub = p.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("version", help="Show version")
    sub.add_parser("instances", help="List all instances")

    add = sub.add_parser("set-default", help="Set the default instance")
    add.add_argument("name", help="Instance name")

    add = sub.add_parser("build", help="Set up yolo-cage (clone repo, build VM)")
    add.add_argument("--config-file", metavar="FILE", help="Path to config.env")
    add.add_argument("--interactive", action="store_true", help="Prompt for config")
    add.add_argument("--up", action="store_true", help="Keep VM running after build")

    add = sub.add_parser("upgrade", help="Upgrade to latest version")
    add.add_argument("--rebuild", action="store_true", help="Rebuild VM after upgrade")

    sub.add_parser("up", help="Start the VM", aliases=["start"])
    sub.add_parser("down", help="Stop the VM", aliases=["stop", "halt"])
    sub.add_parser("destroy", help="Destroy the VM")
    sub.add_parser("status", help="Show VM and pod status")

    add = sub.add_parser("configure", help="Update configuration")
    add.add_argument("--interactive", "-i", action="store_true", help="Prompt for config")

    for cmd_name, aliases, help_text in [
        ("create", [], "Create a sandbox pod"),
        ("attach", [], "Start interactive Claude session"),
        ("shell", ["sh"], "Open shell in sandbox"),
        ("delete", ["rm"], "Delete a sandbox pod"),
        ("logs", [], "Tail pod logs"),
    ]:
        add = sub.add_parser(cmd_name, help=help_text, aliases=aliases)
        add.add_argument("branch", help="Git branch name")
        if cmd_name == "delete":
            add.add_argument("--clean", action="store_true", help="Delete workspace files")

    sub.add_parser("list", help="List sandbox pods", aliases=["ls"])

    add = sub.add_parser("port-forward", help="Forward port from sandbox")
    add.add_argument("branch", help="Git branch name")
    add.add_argument("port", help="PORT or LOCAL:POD")
    add.add_argument("--bind", default="127.0.0.1", metavar="ADDR", help="Bind address")

    args = p.parse_args()
    args.parser = p
    return args


def prompt_config() -> Config:
    """Prompt user for configuration interactively."""
    print("yolo-cage configuration\n")

    pat = input("GitHub PAT: ").strip()
    if not pat:
        die("GitHub PAT is required")

    repo = input("Repository URL: ").strip()
    if not repo:
        die("Repository URL is required")

    log_step("Validating repository access...")
    valid, message = validate_github_repo(repo, pat)
    if not valid:
        die(message)
    log_success(message)

    git_name = input("Git name [yolo-cage]: ").strip() or "yolo-cage"
    git_email = input("Git email [yolo-cage@localhost]: ").strip() or "yolo-cage@localhost"
    proxy_bypass = input("Proxy bypass domains (optional): ").strip()

    return Config(
        github_pat=pat,
        repo_url=repo,
        git_name=git_name,
        git_email=git_email,
        proxy_bypass=proxy_bypass,
    )


# --- Global commands ---

@command("version")
def cmd_version(args, registry, instance):
    print(f"yolo-cage {__version__}")


@command("instances")
def cmd_instances(args, registry, instance):
    instances = registry.list()
    if not instances:
        print("No instances found.\nRun 'yolo-cage build --interactive --up' to create one.")
        return

    print("Instances:")
    for inst in instances:
        marker = " *" if inst.name == registry.default_name else ""
        print(f"  {inst.name}{marker}")
    print("\n* = default instance")


@command("set-default")
def cmd_set_default(args, registry, instance):
    registry.set_default(args.name)
    log_success(f"Default instance set to '{args.name}'")


@command("build")
def cmd_build(args, registry, instance):
    if sys.platform == "darwin":
        print(f"\n{YELLOW}Note: Apple Silicon support is experimental.{NC}\n")

    instances = registry.list()
    if instances and not args.instance:
        names = ", ".join(i.name for i in instances)
        die(f"Instance exists. Use --instance=<name>.\nExisting: {names}")

    if args.config_file:
        config = Config.load(Path(args.config_file))
        if not config:
            die(f"Invalid config file: {args.config_file}")
    elif args.interactive:
        config = prompt_config()
    else:
        config = None

    local_repo = registry.detect_local_repo()
    if local_repo and not registry.is_repo_in_use(local_repo):
        log_step(f"Using local repository: {local_repo}")
    elif local_repo:
        log_step("Local repo already in use, cloning instead...")

    log_step("Building VM (this may take a while)...")
    inst = services.build(registry, args.instance, config, args.up)

    if args.up:
        log_success("VM built and running!")
        print("Create a sandbox:  yolo-cage create <branch>")
    else:
        log_success("VM built successfully!")
        print("Run 'yolo-cage up' to start the VM.")


@command("upgrade")
def cmd_upgrade(args, registry, instance):
    log_step("Downloading latest CLI...")
    services.upgrade_cli(Path("/usr/local/bin/yolo-cage"))
    log_success("CLI updated")

    inst = registry.get(args.instance or registry.default_name)
    if inst:
        if services.upgrade_repo(inst):
            log_success(f"Repository updated for '{inst.name}'")
        else:
            print(f"Skipping repo update for '{inst.name}' (local repo)")

        if args.rebuild:
            log_step(f"Rebuilding VM for '{inst.name}'...")
            services.rebuild_vm(inst)
            log_success("VM rebuilt")


# --- VM lifecycle commands ---

@command("up", requires="exists", aliases=["start"])
def cmd_up(args, registry, instance):
    log_step(f"Starting VM for '{instance.name}'...")
    instance.vm.start()
    log_success("VM is running")
    print("\nCreate a sandbox:  yolo-cage create <branch>")


@command("down", requires="exists", aliases=["stop", "halt"])
def cmd_down(args, registry, instance):
    log_step(f"Stopping VM for '{instance.name}'...")
    instance.vm.stop()
    log_success("VM stopped")


@command("destroy", requires="exists")
def cmd_destroy(args, registry, instance):
    print(f"This will destroy the VM for '{instance.name}' and all data inside it.")
    if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
        print("Aborted.")
        return
    log_step("Destroying VM...")
    instance.vm.destroy()
    log_success("VM destroyed")


@command("status", requires="exists")
def cmd_status(args, registry, instance):
    print(f"Instance: {instance.name}")
    print(f"  Repository: {instance.repo_dir}")
    print(f"  VM status: {instance.vm.status}")
    if instance.vm.status == "running":
        print("\n  Pods:")
        instance.vm.ssh("yolo-cage-inner list")


@command("configure", requires="exists")
def cmd_configure(args, registry, instance):
    if args.interactive:
        config = prompt_config()
        config.save(instance.config_path)
        log_success(f"Config written to {instance.config_path}")
    else:
        config = instance.config
        if not config:
            die(f"No config at {instance.config_path}. Use --interactive.")
        services.validate_config(config)
        log_success("Config validated")

    if instance.vm.status == "running":
        log_step("Syncing configuration to VM...")
        services.sync_config(instance)
        log_success("Config synced")
    else:
        print("VM not running. Config will apply on next 'yolo-cage up'.")


# --- Pod commands ---

@command("create", requires="running")
def cmd_create(args, registry, instance):
    config = instance.config
    if not config:
        die("Missing configuration. Run 'yolo-cage configure'.")
    services.validate_config(config)
    log_success("Config validated")

    instance.vm.ssh(f"yolo-cage-inner create '{args.branch}'")

    prefix = f"-I {instance.name} " if instance.name != registry.default_name else ""
    print(f"Run: yolo-cage {prefix}attach {args.branch}")


@command("attach", requires="running")
def cmd_attach(args, registry, instance):
    instance.vm.ssh(f"yolo-cage-inner attach '{args.branch}'", interactive=True)


@command("shell", requires="running", aliases=["sh"])
def cmd_shell(args, registry, instance):
    instance.vm.ssh(f"yolo-cage-inner shell '{args.branch}'", interactive=True)


@command("list", requires="running", aliases=["ls"])
def cmd_list(args, registry, instance):
    instance.vm.ssh("yolo-cage-inner list")


@command("delete", requires="running", aliases=["rm"])
def cmd_delete(args, registry, instance):
    cmd = f"yolo-cage-inner delete '{args.branch}'"
    if args.clean:
        cmd += " --clean"
    instance.vm.ssh(cmd)


@command("logs", requires="running")
def cmd_logs(args, registry, instance):
    instance.vm.ssh(f"yolo-cage-inner logs '{args.branch}'")


@command("port-forward", requires="running")
def cmd_port_forward(args, registry, instance):
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
    ssh_cmd = ["vagrant", "ssh", "--", "-L",
               f"{args.bind}:{local_port}:localhost:{local_port}", kubectl_cmd]
    try:
        subprocess.call(ssh_cmd, cwd=instance.repo_dir)
    except KeyboardInterrupt:
        print("\nPort forwarding stopped.")


if __name__ == "__main__":
    main()
