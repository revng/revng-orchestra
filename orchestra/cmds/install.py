from loguru import logger

from .common import build_options, execution_options
from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser(
        "install",
        handler=handle_install,
        help="Build and install a component",
        parents=[build_options, execution_options],
    )
    cmd_parser.add_argument("components", nargs="+", help="Name of the components to install")
    cmd_parser.add_argument("--no-force", action="store_true", help="Don't force execution of the root action")
    cmd_parser.add_argument("--no-deps", action="store_true", help="Only execute the requested action")
    cmd_parser.add_argument("--no-merge", action="store_true", help="Do not merge files into orchestra root")
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
    )

    actions = set()
    for component in args.components:
        build = config.get_build(component)
        if not build:
            suggested_component_name = config.get_suggested_component_name(component)
            logger.error(f"Component {component} not found! Did you mean {suggested_component_name}?")
            return 1
        actions.add(build.install)

    executor = Executor(actions, no_deps=args.no_deps, no_force=args.no_force, pretend=args.pretend)
    failed = executor.run()
    exitcode = 1 if failed else 0
    return exitcode
