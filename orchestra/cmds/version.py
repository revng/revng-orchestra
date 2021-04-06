from ..version import __version__


def install_subcommand(sub_argparser):
    sub_argparser.add_parser("version", handler=handle_version, help="Print orchestra version")


def handle_version(args):
    print(__version__)
    return 0
