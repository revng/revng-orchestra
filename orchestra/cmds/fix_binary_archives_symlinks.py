from . import SubCommandParser
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "fix-binary-archives-symlinks",
        handler=handle_fix_binary_archives_symlinks,
        help="Fix symlinks in binary archives",
    )


def handle_fix_binary_archives_symlinks(args):
    config = Configuration(use_config_cache=args.config_cache)

    for _, component in config.components.items():
        for _, build in component.builds.items():
            build.install.update_binary_archive_symlink()

    return 0
