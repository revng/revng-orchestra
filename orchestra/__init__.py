import sys
from loguru import logger
from tqdm import tqdm

from orchestra.cmds.main import main_parser, main_subparsers


class TqdmWrapper:
    def write(self, message):
        tqdm.write(message.strip())
        sys.stdout.flush()
        sys.stderr.flush()


def main():
    args = main_parser.parse_args()

    logger.remove(0)
    logger.add(TqdmWrapper(), level=args.loglevel, colorize=True, format="<level>[+] {level}</level> - {message}")

    cmd_parser = main_subparsers.choices.get(args.command_name)
    if not cmd_parser:
        main_parser.print_help()
        exit(1)

    return cmd_parser.handler(args)
