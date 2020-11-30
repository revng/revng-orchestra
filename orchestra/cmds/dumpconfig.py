from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    sub_argparser.add_parser("dumpconfig", handler=handle_dumpconfig, help="Dump yaml configuration")


def handle_dumpconfig(args):
    config = Configuration(use_config_cache=args.config_cache)
    print(config.generated_yaml)
