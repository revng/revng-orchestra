import argparse

from . import components
from . import environment
from . import clone
from . import configure
from . import install
from . import uninstall
from . import graph
from . import shell


class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, handler=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not handler:
            raise ValueError("Please provide a command handler")
        self.handler = handler


def install_subcommands(argparser):
    subparsers = argparser.add_subparsers(
        description="Available subcommands. Use <subcommand> --help",
        dest="command_name",
        parser_class=CustomArgumentParser)
    components.install_subcommand(subparsers)
    environment.install_subcommand(subparsers)
    clone.install_subcommand(subparsers)
    configure.install_subcommand(subparsers)
    install.install_subcommand(subparsers)
    uninstall.install_subcommand(subparsers)
    graph.install_subcommand(subparsers)
    shell.install_subcommand(subparsers)
    return subparsers
