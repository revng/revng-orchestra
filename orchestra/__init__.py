import os
import sys

from loguru import logger
from tqdm import tqdm

import orchestra.globals
from orchestra.cmds.main import main_parser


class TqdmWrapper:
    def write(self, message):
        tqdm.write(message.strip())
        sys.stdout.flush()
        sys.stderr.flush()


def _main(argv):
    args = main_parser.parse_args(argv)

    # Remove all handlers before installing ours
    logger.remove()
    logger.add(
        TqdmWrapper(),
        level=args.loglevel,
        colorize=True,
        format="<level>[+] {level}</level> - {message}",
    )
    orchestra.globals.loglevel = args.loglevel

    if args.orchestra_dir:
        os.chdir(args.orchestra_dir)

    return_code = main_parser.parse_and_execute(argv)
    if not isinstance(return_code, int):
        raise Exception(f"Handler for command {args.command_name} did not return an integer return code")
    return return_code


def main():
    return _main(sys.argv[1:])
