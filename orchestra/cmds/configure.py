from loguru import logger

from .common import execution_options, build_options
from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("configure",
                                          handler=handle_configure,
                                          help="Run configure script",
                                          parents=[execution_options, build_options]
                                          )
    cmd_parser.add_argument("component", help="Name of the component to configure")
    cmd_parser.add_argument("--no-force", action="store_true", help="Don't force execution of the root action")
    cmd_parser.add_argument("--no-deps", action="store_true", help="Only execute the requested action")


def handle_configure(args):
    config = Configuration(fallback_to_build=args.fallback_build,
                           force_from_source=args.from_source,
                           use_config_cache=args.config_cache,
                           )
    build = config.get_build(args.component)

    if not build:
        suggested_component_name = config.get_suggested_component_name(args.component)
        logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
        exit(1)

    executor = Executor(args)
    return executor.run(build.configure, no_force=args.no_force, no_deps=args.no_deps)
