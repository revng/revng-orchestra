from loguru import logger

from ..model.configuration import Configuration
from ..util import export_environment


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("environment", handler=handle_environment, help="Print environment variables")
    cmd_parser.add_argument("component", nargs="?")


def handle_environment(args):
    config = Configuration(args)
    if not args.component:
        print(export_environment(config.global_env()))
    else:
        build = config.get_build(args.component)

        if not build:
            suggested_component_name = config.get_suggested_component_name(args.component)
            logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
            exit(1)

        print(export_environment(build.install.environment))
