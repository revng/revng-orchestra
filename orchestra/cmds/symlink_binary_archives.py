from . import SubCommandParser
from ..model.configuration import Configuration

from loguru import logger


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "symlink-binary-archives",
        handler=handle_symlink_binary_archives,
        help="Add convenience symlinks in the binary archives",
    )
    cmd_parser.add_argument("name", help="Name of the symlink to link to")


def handle_symlink_binary_archives(args):
    config = Configuration(use_config_cache=args.config_cache)

    for _, component in config.components.items():
        for _, build in component.builds.items():
            logger.info(f"Updating binary archive symlink for {build.qualified_name}")
            build.install.symlink_binary_archive(args.name)

    return 0
