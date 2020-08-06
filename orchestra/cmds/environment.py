from ..environment import export_environment, global_env, per_action_env


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("environment", handler=handle_environment)
    cmd_parser.add_argument("component", nargs="?")


def handle_environment(args, config, index):
    if not args.component:
        print(export_environment(global_env(config)))
    else:
        build = index.get_build(args.component)
        print(export_environment(per_action_env(build.install)))
