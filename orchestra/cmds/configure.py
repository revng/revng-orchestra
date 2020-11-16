from loguru import logger

from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("configure", handler=handle_configure, help="Run configure script")
    cmd_parser.add_argument("component")
    cmd_parser.add_argument("--no-force", action="store_true", help="Don't force execution of the root action")
    cmd_parser.add_argument("--no-deps", action="store_true", help="Only execute the requested action")


def handle_configure(args):
    config = Configuration(args)
    build = config.get_build(args.component)

    if not build:
        suggested_component_name = config.get_suggested_component_name(args.component)
        logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
        exit(1)

    executor = Executor(args)
    executor.run(build.configure, no_force=args.no_force, no_deps=args.no_deps)
