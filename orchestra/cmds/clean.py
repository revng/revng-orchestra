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
    cmd_parser.add_argument("components", nargs="*", help="Name of the components to clean")
    cmd_parser.add_argument("--include-sources", "-s", action="store_true", help="Also delete source dir")
    cmd_parser.add_argument("--all", action="store_true", help="Clean directories for all components")


def clean_all(config: Configuration, args):
    builds_dir = config.builds_dir
    logger.info(f"Cleaning builds dir {builds_dir}")

    if not args.pretend:
        shutil.rmtree(builds_dir, ignore_errors=True)

    if args.include_sources:
        sources_dir = config.sources_dir
        logger.info(f"Cleaning sources dir {sources_dir}")
        if not args.pretend:
            shutil.rmtree(sources_dir, ignore_errors=True)

    return 0


def handle_clean(args):
    config = Configuration(use_config_cache=args.config_cache)

    if bool(args.components) + bool(args.all) != 1:
        logger.error("--all implies all components, do not specify any of them")
        return 1

    if args.all:
        return clean_all(config, args)

    builds = set()
    for component_name in args.components:
        build = config.get_build(component_name)
        if not build:
            suggested_component_name = config.get_suggested_component_name(component_name)
            logger.error(f"Component {component_name} not found! Did you mean {suggested_component_name}?")
            return 1
        builds.add(build)

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
