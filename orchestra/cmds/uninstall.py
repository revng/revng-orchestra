from loguru import logger

from ..model.configuration import Configuration
from ..util import parse_component_name, is_installed
from ..actions.install import uninstall


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("uninstall", handler=handle_uninstall, help="Uninstall a component")
    cmd_parser.add_argument("component")


def handle_uninstall(args, config: Configuration):
    component_name, build_name = parse_component_name(args.component)
    if not is_installed(config, component_name, build_name):
        logger.error(f"Component {args.component} is not installed")

    uninstall(component_name, config)
