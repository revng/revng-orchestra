import argparse
import os
from textwrap import dedent

from loguru import logger

from ..actions.util import run_script
from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("shell", handler=handle_shell,
                                          help="Open a shell with the given component environment (experimental). "
                                               "The shell will start in the component build directory, if it exists. "
                                               "Otherwise, the CWD will not be changed.",
                                          )
    cmd_parser.add_argument("component", nargs="?")
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
            exit(1)

        env = build.install.environment
        ps1_prefix = f"(orchestra - {build.qualified_name}) "
        if os.path.exists(build.install.environment["BUILD_DIR"]):
            cd_to = build.install.environment["BUILD_DIR"]
        else:
            cd_to = os.getcwd()

    if command:
        p = run_script(" ".join(command), environment=env, strict_flags=False, check_returncode=False, cwd=cd_to)
        exit(p.returncode)

    user_shell = run_script("getent passwd $(whoami) | cut -d: -f7", quiet=True).stdout.decode("utf-8").strip()
    env["OLD_HOME"] = os.environ["HOME"]
    env["HOME"] = os.path.join(os.path.dirname(__file__), "..", "support", "shell-home")
    env["PS1_PREFIX"] = ps1_prefix
    script = dedent(f"""
    {user_shell}
    """)
    run_script(script, environment=env, cwd=cd_to)
