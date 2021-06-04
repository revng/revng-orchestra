import os
import sys

from loguru import logger
from tqdm import tqdm

import orchestra.globals
from orchestra.cmds.main import main_parser
from orchestra.exceptions import OrchestraException


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
    orchestra.globals.quiet = args.quiet

    if args.orchestra_dir:
        os.chdir(args.orchestra_dir)

    try:
        return_code = main_parser.parse_and_execute(argv)
        assert isinstance(return_code, int), f"Handler for command {args.command_name} did not return an integer"
        return return_code
    except OrchestraException as e:
        e.log_error()
    except Exception as e:
        logger.exception(e)

    return 100


def main():
    return _main(sys.argv[1:])
