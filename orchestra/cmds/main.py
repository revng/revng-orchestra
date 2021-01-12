import argparse

from . import clean
from . import clone
from . import components
from . import configure
from . import dumpconfig
from . import environment
from . import fix_binary_archives_symlinks
from . import graph
from . import install
from . import ls
from . import shell
from . import uninstall
from . import update
from . import upgrade


class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, handler=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not handler:
            raise ValueError("Please provide a command handler")
        self.handler = handler


main_parser = argparse.ArgumentParser()
logging_group = main_parser.add_argument_group(title="Logging options")
logging_group.add_argument("--loglevel", "-v", default="INFO",
                           choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

config_group = main_parser.add_argument_group(title="Configuration options")
config_group.add_argument("--no-config-cache", dest="config_cache", default=True, action="store_false",
                          help="Do not cache generated yaml configuration")

main_subparsers = main_parser.add_subparsers(
    description="Available subcommands. Use <subcommand> --help",
    dest="command_name",
    parser_class=CustomArgumentParser,
)
components.install_subcommand(main_subparsers)
environment.install_subcommand(main_subparsers)
clone.install_subcommand(main_subparsers)
configure.install_subcommand(main_subparsers)
install.install_subcommand(main_subparsers)
uninstall.install_subcommand(main_subparsers)
clean.install_subcommand(main_subparsers)
update.install_subcommand(main_subparsers)
upgrade.install_subcommand(main_subparsers)
graph.install_subcommand(main_subparsers)
shell.install_subcommand(main_subparsers)
ls.install_subcommand(main_subparsers)
fix_binary_archives_symlinks.install_subcommand(main_subparsers)
dumpconfig.install_subcommand(main_subparsers)
