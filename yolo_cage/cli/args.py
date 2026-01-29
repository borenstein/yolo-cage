"""Argument parsing for yolo-cage CLI."""

import argparse

from .. import __version__


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
