import argparse

from . import SubCommandParser
from . import binary_archives
from . import clean
from . import clone
from . import components
from . import configure
from . import inspect
from . import environment
from . import fix_binary_archives_symlinks
from . import graph
from . import install
from . import ls
from . import shell
from . import uninstall
from . import update
from . import upgrade
from . import version

main_parser = SubCommandParser()
logging_group = main_parser.add_argument_group(title="Logging options")
logging_group.add_argument(
    "--quiet",
    "-q",
    action="store_true",
    help="Do not show the output of the executed scripts unless they have failed",
)
logging_group.add_argument(
    "--loglevel",
    "-v",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
)

config_group = main_parser.add_argument_group(title="Configuration options")
config_group.add_argument(
    "--no-config-cache",
    dest="config_cache",
    default=True,
    action="store_false",
    help="Do not cache generated yaml configuration",
)
config_group.add_argument(
    "--orchestra-dir",
    "-C",
    help="Behave as if orchestra was launched in this directory",
)

subcommands = [
    components,
    environment,
    clone,
    configure,
    install,
    uninstall,
    clean,
    update,
    upgrade,
    graph,
    shell,
    ls,
    fix_binary_archives_symlinks,
    inspect,
    binary_archives,
    version,
]

for cmd in subcommands:
    cmd.install_subcommand(main_parser)
