from loguru import logger

from . import SubCommandParser
from ..actions.uninstall import uninstall
from ..model.configuration import Configuration
from ..model.install_metadata import is_installed
from ..util import parse_component_name


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd("uninstall", handler=handle_uninstall, help="Uninstall a component")
    cmd_parser.add_argument("components", nargs="+", help="Name of the components to uninstall")


def handle_uninstall(args):
    config = Configuration(use_config_cache=args.config_cache)

    component_names_to_uninstall = set()
    for component_spec in args.components:
        component_name, build_name = parse_component_name(component_spec)
        if not is_installed(config, component_name, build_name):
            logger.info(f"Component {component_spec} is not installed")
        else:
            component_names_to_uninstall.add(component_name)

    for component_name in component_names_to_uninstall:
        logger.info(f"Uninstalling {component_name}")
        uninstall(component_name, config)

    return 0
