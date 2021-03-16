import sys
import os
from loguru import logger
from tqdm import tqdm

from orchestra.cmds.main import main_parser, main_subparsers
import orchestra.globals


class TqdmWrapper:
    def write(self, message):
        tqdm.write(message.strip())
        sys.stdout.flush()
        sys.stderr.flush()


def _main(argv):
    args = main_parser.parse_args(argv)

    # Remove all handlers before installing ours
    logger.remove()
    logger.add(TqdmWrapper(), level=args.loglevel, colorize=True, format="<level>[+] {level}</level> - {message}")
    orchestra.globals.loglevel = args.loglevel

    if args.orchestra_dir:
        os.chdir(args.orchestra_dir)

    cmd_parser = main_subparsers.choices.get(args.command_name)
    if not cmd_parser:
        main_parser.print_help()
        exit(1)

    return cmd_parser.handler(args)


def main():
    return _main(sys.argv[1:])
