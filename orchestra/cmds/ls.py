import os

from loguru import logger

from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("ls",
                                          handler=handle_ls,
                                          help="List orchestra-related directories")
    cmd_parser.add_argument("--git-sources", action="store_true", help="Print directories containing git repositories")
    cmd_parser.add_argument("--binary-archives", action="store_true", help="Print binary archives directories")

def handle_ls(args):
    config = Configuration(args)

    if args.git_sources + args.binary_archives != 1:
        logger.error("Please specify one and one flag only")
        exit(1)

    if args.git_sources:
        for component in config.components.values():
            if not component.clone:
                continue
        
            source_path = os.path.join(config.sources_dir, component.name)
            if not os.path.exists(source_path):
                continue
        
            print(source_path)
    elif args.binary_archives:
        for name in config.binary_archives_remotes.keys():
            path = os.path.join(config.binary_archives_dir, name)
            if os.path.exists(path):
                print(path)
