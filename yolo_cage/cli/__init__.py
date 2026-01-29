"""Command-line interface for yolo-cage."""

import sys

from .. import __version__
from ..core import Registry
from ..errors import YoloCageError, PrerequisitesMissing
from ..ops import format_install_instructions
from ..output import die, log_success

from .args import parse_args
from .handlers import COMMANDS


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
