from loguru import logger

from .common import execution_options
from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser(
        "clone",
        handler=handle_clone,
        help="Clone a component",
        parents=[execution_options],
    )
    cmd_parser.add_argument("component", help="Name of the component to clone")
    cmd_parser.add_argument(
        "--no-force",
        action="store_true",
        help="Don't force execution of the root action",
    )


def handle_clone(args):
    config = Configuration(use_config_cache=args.config_cache)

    build = config.get_build(args.component)
    if not build:
        suggested_component_name = config.get_suggested_component_name(args.component)
        logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
        return 1

    if not build.component.clone:
        logger.error("This component does not have a git repository configured!")
        return 1

    executor = Executor([build.component.clone], no_force=args.no_force, pretend=args.pretend)
    failed = executor.run()
    exitcode = 1 if failed else 0
    return exitcode
