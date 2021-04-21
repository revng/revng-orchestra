import shutil

from loguru import logger

from . import SubCommandParser
from .common import execution_options
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "clean",
        handler=handle_clean,
        help="Remove build/source directories",
        parents=[execution_options],
    )
    cmd_parser.add_argument("components", nargs="+", help="Name of the components to clean")
    cmd_parser.add_argument("--include-sources", "-s", action="store_true", help="Also delete source dir")


def handle_clean(args):
    config = Configuration(use_config_cache=args.config_cache)

    builds = []
    for component_name in args.components:
        build = config.get_build(component_name)
        if not build:
            suggested_component_name = config.get_suggested_component_name(component_name)
            logger.error(f"Component {component_name} not found! Did you mean {suggested_component_name}?")
            return 1
        builds.append(build)

    for build in builds:
        build_dir = build.install.environment["BUILD_DIR"]
        logger.info(f"Cleaning build dir for {build.qualified_name} ({build_dir})")

        if not args.pretend:
            shutil.rmtree(build_dir, ignore_errors=True)

        if args.include_sources:
            sources_dir = build.install.environment["SOURCE_DIR"]
            logger.info(f"Cleaning source dir for {build.qualified_name} ({sources_dir})")
            if not args.pretend:
                shutil.rmtree(sources_dir, ignore_errors=True)

    return 0
