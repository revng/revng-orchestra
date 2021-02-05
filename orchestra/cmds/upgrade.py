from .common import execution_options
from ..executor import Executor
from ..model.configuration import Configuration
from ..util import get_installed_metadata


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("upgrade",
                                          handler=handle_upgrade,
                                          help="Upgrade all manually installed components",
                                          parents=[execution_options],
                                          )
    cmd_parser.add_argument("--test", action="store_true", help="Run the test suite")


def handle_upgrade(args):
    config = Configuration(use_config_cache=args.config_cache)

    install_actions = set()

    for component_name, component in config.components.items():
        metadata = get_installed_metadata(component_name, config)
        if metadata is None:
            continue

        if metadata.get("manually_installed", False):
            installed_build_name = metadata["build_name"]
            install_actions.add(component.builds[installed_build_name].install)

    args.keep_tmproot = False
    args.no_merge = False
    executor = Executor(args, install_actions, no_force=True)
    failed = executor.run()
    exitcode = 1 if failed else 0
    return exitcode
