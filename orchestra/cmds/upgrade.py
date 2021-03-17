from .common import execution_options, build_options
from ..executor import Executor
from ..model.configuration import Configuration
from ..model.install_metadata import load_metadata


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("upgrade",
                                          handler=handle_upgrade,
                                          help="Upgrade all manually installed components",
                                          parents=[execution_options, build_options],
                                          )


def handle_upgrade(args):
    config = Configuration(
        fallback_to_build=args.fallback_build,
        force_from_source=args.from_source,
        use_config_cache=args.config_cache,
        run_tests=args.test,
    )

    install_actions = set()

    for component_name, component in config.components.items():
        metadata = load_metadata(component_name, config)
        if metadata is None:
            continue

        if metadata.manually_installed:
            install_actions.add(component.builds[metadata.build_name].install)

    args.keep_tmproot = False
    args.no_merge = False
    executor = Executor(install_actions, no_force=True, pretend=args.pretend)
    failed = executor.run()
    exitcode = 1 if failed else 0
    return exitcode
