import argparse
import os
import os.path
import shlex
from textwrap import dedent

from loguru import logger

from . import SubCommandParser
from ..actions.util import get_script_output
from ..actions.util.impl import _run_script
from ..model.configuration import Configuration
from ..exceptions import UserException


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "shell",
        handler=handle_shell,
        help="Spawn a shell with orchestra environment",
    )
    cmd_parser.add_argument("--component", "-c", help="Source the environment variables specific to this component")
    cmd_parser.add_argument("command", nargs=argparse.REMAINDER)


def handle_shell(args):
    config = Configuration(use_config_cache=args.config_cache)
    command = args.command

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
        cd_to = build.install.environment["BUILD_DIR"]
        if not os.path.isdir(cd_to):
            raise UserException(f"Build directory for component {build.qualified_name} does not exist")

    if command:
        script_to_run = " ".join(shlex.quote(c) for c in command)
        p = _run_script(
            script_to_run,
            environment=env,
            strict_flags=False,
            cwd=cd_to,
            loglevel="DEBUG",
        )
        return p.returncode

    user_shell = get_script_output("getent passwd $(whoami) | cut -d: -f7").strip()

    if not os.access(user_shell, os.X_OK):
        logger.error("Current user has no shell available, falling back to /bin/sh")
        user_shell = "/bin/sh"

    env["OLD_HOME"] = os.environ["HOME"]
    env["HOME"] = os.path.join(os.path.dirname(__file__), "..", "support", "shell-home")
    env["PS1_PREFIX"] = ps1_prefix
    script = dedent(f"exec {user_shell}")
    result = _run_script(script, environment=env, loglevel="DEBUG", cwd=cd_to)
    return result.returncode
