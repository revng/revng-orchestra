from loguru import logger

from . import SubCommandParser
from .common import execution_options
from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "clone",
        handler=handle_clone,
        help="Clone a component",
        parents=[execution_options],
    )
    cmd_parser.add_argument("components", nargs="+", help="Name of the components to clone")
    cmd_parser.add_argument("--no-force", action="store_true", help="Don't force execution of the root action")


def handle_clone(args):
    config = Configuration(use_config_cache=args.config_cache)

    actions = set()
    for component in args.components:
        build = config.get_build(component)
        if not build:
            suggested_component_name = config.get_suggested_component_name(component)
            logger.error(f"Component {component} not found! Did you mean {suggested_component_name}?")
            return 1

        if not build.component.clone:
            logger.error("This component does not have a git repository configured!")
            return 1

        actions.add(build.component.clone)

    executor = Executor(actions, no_force=args.no_force, pretend=args.pretend)
    failed = executor.run()
    exitcode = 1 if failed else 0
    return exitcode
