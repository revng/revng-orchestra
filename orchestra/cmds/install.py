from loguru import logger

from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("install", handler=handle_install, help="Build and install a component")
    cmd_parser.add_argument("component")
    cmd_parser.add_argument("--force", "-f", action="store_true", help="Force execution of the root action")
    cmd_parser.add_argument("--no-merge", action="store_true", help="Do not merge files into orchestra root")
    cmd_parser.add_argument("--create-binary-archives", action="store_true", help="Create binary archives")
    cmd_parser.add_argument("--keep-tmproot", action="store_true", help="Do not remove temporary root directories")


def handle_install(args, config: Configuration):
    build = config.get_build(args.component)

    if not build:
        suggested_component_name = config.get_suggested_component_name(args.component)
        logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
        exit(1)

    executor = Executor(args)
    executor.run(build.install, force=args.force)
