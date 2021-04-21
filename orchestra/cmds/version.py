from . import SubCommandParser
from ..version import __version__


def install_subcommand(sub_argparser: SubCommandParser):
    sub_argparser.add_subcmd("version", handler=handle_version, help="Print orchestra version")


def handle_version(args):
    print(__version__)
    return 0
