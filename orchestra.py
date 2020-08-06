#!/usr/bin/env python3

import argparse
import logging

from orchestra.cmds import install_subcommands
from orchestra.config import gen_config
from orchestra.model.index import ComponentIndex

parser = argparse.ArgumentParser()
parser.add_argument("--config", default="./config")
# TODO: set default loglevel to INFO or WARNING
parser.add_argument("--loglevel", "-v", default="DEBUG", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
parser.add_argument("--show-output", dest="show_output", action="store_true", help="Show commands output")
subparsers = install_subcommands(parser)


if __name__ == "__main__":
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.loglevel))

    cmd_parser = subparsers.choices.get(args.command_name)
    if not cmd_parser:
        parser.print_help()
        exit(1)

    config = gen_config(args.config)
    index = ComponentIndex(config)

    cmd_parser.handler(args, config, index)
