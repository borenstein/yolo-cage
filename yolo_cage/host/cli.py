"""Command-line interface for yolo-cage."""

import argparse
import sys
from pathlib import Path

__version__ = "dev"


def main() -> None:
    """Main entry point."""
    from .commands.build import cmd_build
    from .commands.config_cmd import cmd_configure
    from .commands.instance import cmd_instances, cmd_set_default, cmd_delete_instance
    from .commands.network import cmd_port_forward
    from .commands.runtime import cmd_up, cmd_down, cmd_destroy, cmd_status
    from .commands.sandbox import cmd_create, cmd_attach, cmd_shell, cmd_list, cmd_delete, cmd_logs

    parser = argparse.ArgumentParser(
        prog="yolo-cage",
        description="Sandboxed Claude Code agents",
    )
    parser.add_argument("--version", "-v", action="version", version=f"yolo-cage {__version__}")
    parser.add_argument("-I", "--instance", metavar="NAME", help="Instance name")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # Instance management
    sub.add_parser("instances", help="List instances").set_defaults(func=cmd_instances)

    p = sub.add_parser("set-default", help="Set default instance")
    p.add_argument("name", help="Instance name")
    p.set_defaults(func=cmd_set_default)

    p = sub.add_parser("delete-instance", help="Delete an instance")
    p.add_argument("name", help="Instance name")
    p.add_argument("-f", "--force", action="store_true", help="Skip confirmation")
    p.set_defaults(func=cmd_delete_instance)

    # Build
    p = sub.add_parser("build", help="Set up yolo-cage")
    p.add_argument("--config-file", type=Path, help="Path to config.env")
    p.add_argument("--interactive", action="store_true", help="Prompt for config")
    p.add_argument("--up", action="store_true", help="Keep VM running after build")
    p.set_defaults(func=cmd_build)

    # Runtime lifecycle
    p = sub.add_parser("up", help="Start VM", aliases=["start"])
    p.set_defaults(func=cmd_up)

    p = sub.add_parser("down", help="Stop VM", aliases=["stop", "halt"])
    p.set_defaults(func=cmd_down)

    p = sub.add_parser("destroy", help="Destroy VM")
    p.set_defaults(func=cmd_destroy)

    p = sub.add_parser("status", help="Show status")
    p.set_defaults(func=cmd_status)

    # Configuration
    p = sub.add_parser("configure", help="Update configuration")
    p.add_argument("-i", "--interactive", action="store_true", help="Prompt for config")
    p.set_defaults(func=cmd_configure)

    # Sandbox operations
    p = sub.add_parser("create", help="Create sandbox")
    p.add_argument("branch", help="Branch name")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("attach", help="Attach to sandbox")
    p.add_argument("branch", help="Branch name")
    p.set_defaults(func=cmd_attach)

    p = sub.add_parser("shell", help="Shell into sandbox", aliases=["sh"])
    p.add_argument("branch", help="Branch name")
    p.set_defaults(func=cmd_shell)

    p = sub.add_parser("list", help="List sandboxes", aliases=["ls"])
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("delete", help="Delete sandbox", aliases=["rm"])
    p.add_argument("branch", help="Branch name")
    p.add_argument("--clean", action="store_true", help="Delete workspace too")
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("logs", help="Show sandbox logs")
    p.add_argument("branch", help="Branch name")
    p.set_defaults(func=cmd_logs)

    # Network
    p = sub.add_parser("port-forward", help="Forward port from sandbox")
    p.add_argument("branch", help="Branch name")
    p.add_argument("port", help="PORT or LOCAL:REMOTE")
    p.add_argument("--bind", default="127.0.0.1", help="Bind address")
    p.set_defaults(func=cmd_port_forward)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
