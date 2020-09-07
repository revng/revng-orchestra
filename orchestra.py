#!/usr/bin/env python3

import argparse
import sys
from loguru import logger

from orchestra.cmds import install_subcommands
from orchestra.model.configuration import Configuration

parser = argparse.ArgumentParser()
# TODO: set default loglevel to INFO or WARNING
parser.add_argument("--loglevel", "-v", default="DEBUG", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
parser.add_argument("--quiet", action="store_true", help="Do not show output of executed commands")
parser.add_argument("--no-config-cache", action="store_true", help="Do not cache generated yaml configuration")
parser.add_argument("--no-binary-archives", action="store_true", help="Build all components from source")

subparsers = install_subcommands(parser)


if __name__ == "__main__":
    args = parser.parse_args()

    logger.remove(0)
    logger.add(sys.stdout, level=args.loglevel, colorize=True, format="<level>[+] {level}</level> - {message}")

    cmd_parser = subparsers.choices.get(args.command_name)
    if not cmd_parser:
        parser.print_help()
        exit(1)

    configuration = Configuration(args)

    cmd_parser.handler(args, configuration)
