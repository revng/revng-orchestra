from loguru import logger

from . import SubCommandParser
from .common import build_options, execution_options
from ..actions.uninstall import uninstall
from ..executor import Executor
from ..gitutils.lfs import assert_lfs_installed
from ..model.configuration import Configuration
from ..model.install_metadata import is_installed


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "install",
        handler=handle_install,
        help="Build and install a component",
        parents=[build_options, execution_options],
    )
    cmd_parser.add_argument("components", nargs="+", help="Name of the components to install")
    cmd_parser.add_argument("--no-force", action="store_true", help="Don't force execution of the root action")
    cmd_parser.add_argument("--no-deps", action="store_true", help="Only execute the requested action")
    cmd_parser.add_argument("--no-merge", action="store_true", help="Do not merge files into orchestra root")
    cmd_parser.add_argument(
        "--no-uninstall-dependants",
        action="store_true",
        help="Do not uninstall components that depend on the ones being reinstalled",
    )
    cmd_parser.add_argument("--create-binary-archives", action="store_true", help="Create binary archives")
    cmd_parser.add_argument(
        "--keep-tmproot",
        action="store_true",
        help="Do not remove temporary root directories",
    )


def handle_install(args):
    config = Configuration(
        fallback_to_build=args.fallback_build,
        force_from_source=args.from_source,
        use_config_cache=args.config_cache,
        create_binary_archives=args.create_binary_archives,
        no_merge=args.no_merge,
        keep_tmproot=args.keep_tmproot,
        run_tests=args.test,
        max_lfs_retries=args.lfs_retries,
        discard_build_directories=args.discard_build_directories,
    )

    assert_lfs_installed()

    actions = []
    for component in args.components:
        build = config.get_build(component)
        if not build:
            suggested_component_name = config.get_suggested_component_name(component)
            logger.error(f"Component {component} not found! Did you mean {suggested_component_name}?")
            return 1

        actions.append(build.install)

        for trigger in build.component.triggers:
            actions.append(config.get_build(trigger).install)

    # Uninstall dependants
    components_to_uninstall = set()
    for action in actions:
        target_component = action.build.component
        for component in config.components.values():
            if component is target_component:
                continue
            if target_component in component._transitive_dependencies() and is_installed(config, component.name):
                components_to_uninstall.add(component)

    if not args.no_uninstall_dependants and components_to_uninstall:
        for component_to_uninstall in components_to_uninstall:
            logger.info(f"""Uninstalling {component_to_uninstall.name}""")
            if not args.pretend:
                uninstall(component_to_uninstall.name, config)

    for action in actions:
        executor = Executor([action], no_deps=args.no_deps, no_force=args.no_force, pretend=args.pretend)
        failed = executor.run()
        if failed:
            return 1

    return 0
