from loguru import logger

from ..model.configuration import Configuration
from ..util import parse_component_name, is_installed
from ..actions.install import uninstall


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("dumpconfig", handler=handle_dumpconfig, help="Dump yaml configuration")


def handle_dumpconfig(args, config: Configuration):
    print(config.generated_yaml)
