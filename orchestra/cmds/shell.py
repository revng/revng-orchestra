import argparse
import os
import shlex
from textwrap import dedent

from loguru import logger

from . import SubCommandParser
from ..actions.util import get_script_output
from ..actions.util.impl import _run_script
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "shell",
        handler=handle_shell,
        help="Open a shell with orchestra environment (experimental).",
    )
    cmd_parser.add_argument(
        "--component",
        "-c",
        help="Execute in the context of this component. "
        "The shell will start in the component build directory, if it exists. "
        "Otherwise, the CWD will not be changed.",
    )
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
        if os.path.exists(build.install.environment["BUILD_DIR"]):
            cd_to = build.install.environment["BUILD_DIR"]
        else:
            cd_to = os.getcwd()

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

    env["OLD_HOME"] = os.environ["HOME"]
    env["HOME"] = os.path.join(os.path.dirname(__file__), "..", "support", "shell-home")
    env["PS1_PREFIX"] = ps1_prefix
    script = dedent(f"exec {user_shell}")

    result = _run_script(script, environment=env, loglevel="DEBUG", cwd=cd_to)
    return result.returncode
