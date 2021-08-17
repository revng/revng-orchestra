from loguru import logger

from . import SubCommandParser
from .common import execution_options, build_options
from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "configure",
        handler=handle_configure,
        help="Run configure script",
        parents=[execution_options, build_options],
    )
    cmd_parser.add_argument("components", nargs="+", help="Name of the components to configure")
    cmd_parser.add_argument("--no-force", action="store_true", help="Don't force execution of the root action")
    cmd_parser.add_argument("--no-deps", action="store_true", help="Only execute the requested action")


def handle_configure(args):
    config = Configuration(
        fallback_to_build=args.fallback_build,
        force_from_source=args.from_source,
        use_config_cache=args.config_cache,
        run_tests=args.test,
        max_lfs_retries=args.lfs_retries,
    )

    actions = set()
    for component in args.components:
        build = config.get_build(component)

        if not build:
            suggested_component_name = config.get_suggested_component_name(component)
            logger.error(f"Component {component} not found! Did you mean {suggested_component_name}?")
            return 1

        actions.add(build.configure)

    executor = Executor(actions, no_deps=args.no_deps, no_force=args.no_force, pretend=args.pretend)

    failed = executor.run()
    exitcode = 1 if failed else 0
    return exitcode
