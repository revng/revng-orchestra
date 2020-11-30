import os
import pty
import select
import sys
import termios
import tty
from subprocess import Popen
from textwrap import dedent

from loguru import logger

from ..actions.util import run_script
from ..model.configuration import Configuration
from ..util import export_environment


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("shell", handler=handle_shell,
                                          help="Open a shell with the given component environment (experimental)")
    cmd_parser.add_argument("component", nargs="?")


def handle_shell(args):
    config = Configuration(args)
    if not args.component:
        env = config.global_env()
        ps1_prefix = "(orchestra) "
        cd_to = os.getcwd()
    else:
        build = config.get_build(args.component)

        if not build:
            suggested_component_name = config.get_suggested_component_name(args.component)
            logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
            return 1

        env = build.install.environment
        ps1_prefix = f"(orchestra - {build.qualified_name}) "
        if os.path.exists(build.install.environment["BUILD_DIR"]):
            cd_to = build.install.environment["BUILD_DIR"]
        else:
            cd_to = os.getcwd()

    user_shell = run_script("getent passwd $(whoami) | cut -d: -f7", quiet=True).stdout.decode("utf-8").strip()
    env["OLD_HOME"] = os.environ["HOME"]
    env["HOME"] = os.path.join(os.path.dirname(__file__), "..", "support", "shell-home")
    env["PS1_PREFIX"] = ps1_prefix
    script = dedent(f"""
    cd {cd_to}
    {user_shell}
    """)
    run_script(script, environment=env)
