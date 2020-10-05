from ..util import export_environment


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("environment", handler=handle_environment, help="Print environment variables")
    cmd_parser.add_argument("component", nargs="?")


def handle_environment(args, config):
    if not args.component:
        print(export_environment(config.global_env()))
    else:
        build = config.get_build(args.component)
        print(export_environment(build.install.environment))
