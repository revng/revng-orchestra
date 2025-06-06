import os

from loguru import logger

from . import SubCommandParser
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd("ls", handler=handle_ls, help="List orchestra-related directories")
    cmd_parser.add_argument(
        "--git-sources",
        action="store_true",
        help="Print directories containing git repositories",
    )
    cmd_parser.add_argument(
        "--binary-archives",
        action="store_true",
        help="Print binary archives directories",
    )


def handle_ls(args):
    config = Configuration(use_config_cache=args.config_cache)

    if args.git_sources + args.binary_archives != 1:
        logger.error("Please specify one and one flag only")
        return 1

    if args.git_sources:
        for clone_action in config.repositories.values():
            if clone_action.source_dir is not None:
                print(clone_action.source_dir)

    elif args.binary_archives:
        for name in config.binary_archives_remotes.keys():
            path = os.path.join(config.binary_archives_dir, name)
            if os.path.exists(path):
                print(path)

    return 0
