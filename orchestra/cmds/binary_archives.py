import os

from loguru import logger

from . import SubCommandParser
from .fix_binary_archives_symlinks import handle_fix_binary_archives_symlinks
from ..actions.util import get_script_output
from ..gitutils import is_root_of_git_repo
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "binary-archives",
        help="Manipulate binary archives",
    )
    ls_subcmd = cmd_parser.add_subcmd(
        "ls",
        handler=handle_ls,
        help="Print binary archives directories",
    )

    ls_subcmd.add_argument(
        "--include-non-cloned",
        "-a",
        action="store_true",
        help="Include binary archives that have not yet been cloned (nonexisting paths)",
    )

    cmd_parser.add_subcmd(
        "fix-symlinks",
        handler=handle_fix_binary_archives_symlinks,
        help="Fix symlinks in binary archives",
    )

    clean_subcmd = cmd_parser.add_subcmd("clean", handler=handle_clean, help="Delete stale binary archives")
    clean_subcmd.add_argument(
        "--pretend",
        action="store_true",
        help="Only print what would be done. Deleted files are printed at DEBUG loglevel",
    )


def handle_clean(args):
    config = Configuration(use_config_cache=args.config_cache)
    for name, path in config.binary_archives_local_paths.items():
        if is_root_of_git_repo(path):
            logger.info(f"Cleaning binary archive {name}")
            unneeded_files = find_unreferenced_archives(path)

            for file in unneeded_files:
                abspath = os.path.join(path, file)
                if os.path.exists(abspath):
                    logger.debug(f"Deleting {file}")
                    if not args.pretend:
                        os.unlink(abspath)

        elif os.path.exists(path):
            logger.warning(f"Path {path} is not the root of a git repository, skipping")

    return 0


def handle_ls(args):
    config = Configuration(use_config_cache=args.config_cache)
    for name in config.binary_archives_remotes.keys():
        path = os.path.join(config.binary_archives_dir, name)
        if args.include_non_cloned or os.path.exists(path):
            print(path)
    return 0


def find_unreferenced_archives(binary_archive_path):
    """Finds archives tracked by git-lfs but not referenced by any symlink
    :param binary_archive_path: path to the binary archive git lfs repository
    :return: a set of paths of the unreferenced files. The paths are relative to binary_archive_path.
    """

    all_tracked_files = set(get_script_output(f"git lfs ls-files -n", cwd=binary_archive_path).splitlines())

    files_still_linked = set()
    for dirpath, dirnames, filenames in os.walk(binary_archive_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.islink(filepath):
                link_dst = os.readlink(filepath)
                if os.path.isabs(link_dst):
                    logger.warning(f"Symlink {filepath} points to absolute path {link_dst}")
                else:
                    absolute_link_dst = os.path.realpath(os.path.join(dirpath, link_dst))
                    relative_link_dst = os.path.relpath(absolute_link_dst, binary_archive_path)
                    files_still_linked.add(relative_link_dst)

    return all_tracked_files - files_still_linked
