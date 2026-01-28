"""Command-line interface for yolo-cage."""

import argparse
import sys

from . import __version__

INSTANCE_EPILOG = "Use -I/--instance NAME before the command to target a specific instance."
from .commands.build import cmd_build
from .commands.vm import cmd_up, cmd_down, cmd_destroy, cmd_status
from .commands.pods import cmd_create, cmd_attach, cmd_shell, cmd_list, cmd_delete, cmd_logs
from .commands.config_cmd import cmd_configure
from .commands.network import cmd_port_forward
from .commands.manage import cmd_instances, cmd_set_default, cmd_upgrade, cmd_version


def main() -> None:
    """Main entry point for yolo-cage CLI."""
    parser = argparse.ArgumentParser(
        prog="yolo-cage",
        description="Sandboxed Claude Code agents",
    )
    parser.add_argument(
        "--version",
        "-v",
        "--v",
        action="version",
        version=f"yolo-cage {__version__}",
    )
    parser.add_argument(
        "--instance",
        "-I",
        metavar="NAME",
        help="Instance name (default: use default instance)",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # version (subcommand alias for --version)
    p_version = subparsers.add_parser(
        "version",
        help="Show version",
    )
    p_version.set_defaults(func=cmd_version)

    # build
    p_build = subparsers.add_parser(
        "build",
        help="Set up yolo-cage (clone repo, build VM)",
        description="Set up yolo-cage by cloning the repository and building the VM.",
    )
    p_build.add_argument(
        "--config-file",
        metavar="FILE",
        help="Path to config.env file",
    )
    p_build.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for configuration interactively",
    )
    p_build.add_argument(
        "--up",
        action="store_true",
        help="Keep VM running after build",
    )
    p_build.add_argument(
        "--instance",
        "-I",
        metavar="NAME",
        help="Instance name (default: 'default' for first instance)",
    )
    p_build.set_defaults(func=cmd_build)

    # instances
    p_instances = subparsers.add_parser(
        "instances",
        help="List all instances",
    )
    p_instances.set_defaults(func=cmd_instances)

    # set-default
    p_set_default = subparsers.add_parser(
        "set-default",
        help="Set the default instance",
    )
    p_set_default.add_argument("name", help="Instance name")
    p_set_default.set_defaults(func=cmd_set_default)

    # upgrade
    p_upgrade = subparsers.add_parser(
        "upgrade",
        help="Upgrade to latest version",
        description="Download the latest CLI, update the repo, and optionally rebuild the VM.",
    )
    p_upgrade.add_argument(
        "--rebuild",
        action="store_true",
        help="Also rebuild the VM after upgrading",
    )
    p_upgrade.set_defaults(func=cmd_upgrade)

    # up
    p_up = subparsers.add_parser(
        "up",
        help="Start the VM",
        aliases=["start"],
        epilog=INSTANCE_EPILOG,
    )
    p_up.add_argument(
        "--ram",
        metavar="SIZE",
        help="RAM size (not yet implemented)",
    )
    p_up.set_defaults(func=cmd_up)

    # down
    p_down = subparsers.add_parser(
        "down",
        help="Stop the VM",
        aliases=["stop", "halt"],
        epilog=INSTANCE_EPILOG,
    )
    p_down.set_defaults(func=cmd_down)

    # destroy
    p_destroy = subparsers.add_parser(
        "destroy",
        help="Remove the VM entirely",
        description="Destroy the VM and all data inside it. Your config.env will be preserved.",
        epilog=INSTANCE_EPILOG,
    )
    p_destroy.set_defaults(func=cmd_destroy)

    # configure
    p_configure = subparsers.add_parser(
        "configure",
        help="Update configuration and sync to VM",
        description="Validate and sync configuration to the VM. Use --interactive to re-enter credentials.",
        epilog=INSTANCE_EPILOG,
    )
    p_configure.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Prompt for configuration interactively",
    )
    p_configure.set_defaults(func=cmd_configure)

    # status
    p_status = subparsers.add_parser(
        "status",
        help="Show VM and pod status",
        epilog=INSTANCE_EPILOG,
    )
    p_status.set_defaults(func=cmd_status)

    # create
    p_create = subparsers.add_parser(
        "create",
        help="Create a sandbox pod for a branch",
        epilog=INSTANCE_EPILOG,
    )
    p_create.add_argument("branch", help="Git branch name")
    p_create.set_defaults(func=cmd_create)

    # attach
    p_attach = subparsers.add_parser(
        "attach",
        help="Start interactive Claude Code session",
        epilog=INSTANCE_EPILOG,
    )
    p_attach.add_argument("branch", help="Git branch name")
    p_attach.set_defaults(func=cmd_attach)

    # shell
    p_shell = subparsers.add_parser(
        "shell",
        help="Open a shell in a sandbox pod",
        aliases=["sh"],
        epilog=INSTANCE_EPILOG,
    )
    p_shell.add_argument("branch", help="Git branch name")
    p_shell.set_defaults(func=cmd_shell)

    # list
    p_list = subparsers.add_parser(
        "list",
        help="List all sandbox pods",
        aliases=["ls"],
        epilog=INSTANCE_EPILOG,
    )
    p_list.set_defaults(func=cmd_list)

    # delete
    p_delete = subparsers.add_parser(
        "delete",
        help="Delete a sandbox pod",
        aliases=["rm"],
        epilog=INSTANCE_EPILOG,
    )
    p_delete.add_argument("branch", help="Git branch name")
    p_delete.add_argument(
        "--clean",
        action="store_true",
        help="Also delete workspace files",
    )
    p_delete.set_defaults(func=cmd_delete)

    # logs
    p_logs = subparsers.add_parser(
        "logs",
        help="Tail pod logs",
        epilog=INSTANCE_EPILOG,
    )
    p_logs.add_argument("branch", help="Git branch name")
    p_logs.set_defaults(func=cmd_logs)

    # port-forward
    p_port_forward = subparsers.add_parser(
        "port-forward",
        help="Forward a port from a sandbox pod",
        description="Forward a port from a sandbox pod to your local machine.",
        epilog=INSTANCE_EPILOG,
    )
    p_port_forward.add_argument("branch", help="Git branch name")
    p_port_forward.add_argument(
        "port",
        help="Port specification: PORT or LOCAL:POD (e.g., 8080 or 9000:3000)",
    )
    p_port_forward.add_argument(
        "--bind",
        default="127.0.0.1",
        metavar="ADDR",
        help="Bind address (default: 127.0.0.1, use 0.0.0.0 for LAN access)",
    )
    p_port_forward.set_defaults(func=cmd_port_forward)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
