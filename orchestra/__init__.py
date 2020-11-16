import argparse
import sys
from loguru import logger
from tqdm import tqdm

from orchestra.cmds import install_subcommands
from orchestra.model.configuration import Configuration

parser = argparse.ArgumentParser()
parser.add_argument("--loglevel", "-v", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
parser.add_argument("--pretend", "-n", action="store_true", help="Do not execute actions, only print what would be done")
parser.add_argument("--quiet", "-q", action="store_true", help="Do not show output of executed commands")
parser.add_argument("--no-config-cache", action="store_true", help="Do not cache generated yaml configuration")
parser.add_argument("--from-source", "-B", action="store_true", help="Build all components from source")
parser.add_argument("--fallback-build", "-b", action="store_true", help="Build if binary archives are not available")

subparsers = install_subcommands(parser)

class TqdmWrapper:
    def write(self, message):
        tqdm.write(message.strip())
        sys.stdout.flush()
        sys.stderr.flush()

def main():
    args = parser.parse_args()

    logger.remove(0)
    logger.add(TqdmWrapper(), level=args.loglevel, colorize=True, format="<level>[+] {level}</level> - {message}")

    cmd_parser = subparsers.choices.get(args.command_name)
    if not cmd_parser:
        parser.print_help()
        exit(1)

    cmd_parser.handler(args)
