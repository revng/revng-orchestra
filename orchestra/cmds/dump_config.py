from ..model.index import ComponentIndex
from ..config import gen_yaml


def install_subcommand(sub_argparser):
    sub_argparser.add_parser("dumpconfig", handler=handle_dump_config)


def handle_dump_config(args, config, index: ComponentIndex):
    print(gen_yaml(args.config).decode("utf-8"))
