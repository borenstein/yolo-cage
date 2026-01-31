"""VM command handlers - CLI interface for VM-side operations."""

import argparse
import sys

from ..errors import SandboxError, YoloCageError
from ..output import die, log_error
from ..domain.branch import Branch
from . import sandbox_ops


def cmd_create(args: argparse.Namespace) -> None:
    """Create a sandbox."""
    branch = Branch(name=args.branch)
    try:
        sandbox_ops.create_sandbox(branch)
    except SandboxError as e:
        die(str(e))


def cmd_list(args: argparse.Namespace) -> None:
    """List all sandboxes."""
    try:
        sandboxes = sandbox_ops.list_sandboxes()

        # Format as table
        print("BRANCH\t\tSTATUS")
        for sandbox in sandboxes:
            print(f"{sandbox.branch.name}\t\t{sandbox.status.value}")

    except SandboxError as e:
        die(str(e))


def cmd_attach(args: argparse.Namespace) -> None:
    """Attach to a sandbox."""
    branch = Branch(name=args.branch)
    try:
        exit_code = sandbox_ops.attach_to_sandbox(branch)
        sys.exit(exit_code)
    except SandboxError as e:
        die(str(e))


def cmd_shell(args: argparse.Namespace) -> None:
    """Open shell in a sandbox."""
    branch = Branch(name=args.branch)
    try:
        exit_code = sandbox_ops.open_shell_in_sandbox(branch)
        sys.exit(exit_code)
    except SandboxError as e:
        die(str(e))


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a sandbox."""
    branch = Branch(name=args.branch)
    try:
        sandbox_ops.delete_sandbox(branch, clean=args.clean)
    except SandboxError as e:
        die(str(e))


def cmd_logs(args: argparse.Namespace) -> None:
    """Tail sandbox logs."""
    branch = Branch(name=args.branch)
    try:
        exit_code = sandbox_ops.tail_sandbox_logs(branch)
        sys.exit(exit_code)
    except SandboxError as e:
        die(str(e))


def main() -> None:
    """Main entry point for VM-side CLI."""
    parser = argparse.ArgumentParser(
        prog="yolo-cage-vm",
        description="VM-side operations for yolo-cage sandboxes",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # create
    p_create = subparsers.add_parser("create", help="Create a sandbox")
    p_create.add_argument("branch", help="Git branch name")
    p_create.set_defaults(func=cmd_create)

    # list
    p_list = subparsers.add_parser("list", help="List all sandboxes", aliases=["ls"])
    p_list.set_defaults(func=cmd_list)

    # attach
    p_attach = subparsers.add_parser("attach", help="Attach to sandbox")
    p_attach.add_argument("branch", help="Git branch name")
    p_attach.set_defaults(func=cmd_attach)

    # shell
    p_shell = subparsers.add_parser("shell", help="Open shell in sandbox", aliases=["sh"])
    p_shell.add_argument("branch", help="Git branch name")
    p_shell.set_defaults(func=cmd_shell)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a sandbox", aliases=["rm"])
    p_delete.add_argument("branch", help="Git branch name")
    p_delete.add_argument("--clean", action="store_true", help="Also delete workspace files")
    p_delete.set_defaults(func=cmd_delete)

    # logs
    p_logs = subparsers.add_parser("logs", help="Tail sandbox logs")
    p_logs.add_argument("branch", help="Git branch name")
    p_logs.set_defaults(func=cmd_logs)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
