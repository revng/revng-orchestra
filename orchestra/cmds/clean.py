import shutil

from loguru import logger

from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("clean", handler=handle_clean, help="Remove build/source directories")
    cmd_parser.add_argument("component")
    cmd_parser.add_argument("--include-sources", "-s", action="store_true", help="Also delete source dir")


def handle_clean(args):
    config = Configuration(args)
    build = config.get_build(args.component)

    if not build:
        suggested_component_name = config.get_suggested_component_name(args.component)
        logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
        exit(1)

    build_dir = build.install.environment["BUILD_DIR"]
    logger.info(f"Cleaning build dir for {build.qualified_name} ({build_dir})")

    if not args.pretend:
        shutil.rmtree(build_dir, ignore_errors=True)

    if args.include_sources:
        sources_dir = build.install.environment["SOURCE_DIR"]
        logger.info(f"Cleaning source dir for {build.qualified_name} ({sources_dir})")
        if not args.pretend:
            shutil.rmtree(sources_dir, ignore_errors=True)
