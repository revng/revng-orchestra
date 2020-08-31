import logging

from ..model.index import ComponentIndex
from ..util import parse_component_name, is_installed
from ..model.actions.install import uninstall


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("uninstall", handler=handle_uninstall)
    cmd_parser.add_argument("component")


def handle_uninstall(args, config, index: ComponentIndex):
    component_name, build_name = parse_component_name(args.component)
    if not is_installed(config, component_name, build_name):
        print(f"Component {args.component} is not installed")
        return

    uninstall(config, component_name)
