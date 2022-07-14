import itertools
from loguru import logger
from shlex import quote

from . import SubCommandParser
from .common import execution_options
from ..actions.util import run_user_script, get_subprocess_output, try_get_subprocess_output
from ..exceptions import UserException
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "check-branch",
        handler=handle_check_branch,
        help="Run lint scripts",
        parents=[execution_options],
    )
    cmd_parser.add_argument("component", help="Name of the components to check")
    cmd_parser.add_argument("--onto", help="Branch (or origin/branch) where the rebase is done onto")


def handle_check_branch(args):
    config = Configuration(use_config_cache=args.config_cache)

    component_name = args.component

    build = config.get_build(component_name)
    if not build:
        suggested_component_name = config.get_suggested_component_name(component_name)
        logger.error(f"Component {component_name} not found! Did you mean {suggested_component_name}?")
        return 1

    found_ancestor = None
    if args.onto:
        found_ancestor = args.onto
    else:
        # Search for an ancestor commit matching these criteria:
        # - it has to be the HEAD of a branch whose name is one of the default branch names
        # - it strictly has to be and ancestor (meaning the curent HEAD commit isn't a valid choice)
        git_remote_output = get_subprocess_output(["git", "remote"], cwd=build.install.source_dir)
        remotes = git_remote_output.strip().splitlines(keepends=False)

        ancestor_candidates = [
            f"{remote}/{branch_name}" for remote, branch_name in itertools.product(remotes, config.branches)
        ]

        returncode, head_commit = try_get_subprocess_output(
            ["git", "rev-parse", "HEAD"],
            cwd=build.install.source_dir,
        )
        if returncode != 0:
            raise UserException(f"Can't execute git rev-parse HEAD, have you cloned {build.qualified_name} sources?")

        second_round = []
        for ancestor_candidate in ancestor_candidates:
            returncode, ancestor_commit = try_get_subprocess_output(
                ["git", "rev-parse", ancestor_candidate],
                cwd=build.install.source_dir,
            )
            if returncode != 0 or ancestor_commit == head_commit:
                continue

            returncode, output = try_get_subprocess_output(
                ["git", "log", "--oneline", f"{ancestor_candidate}..HEAD"],
                cwd=build.install.source_dir,
            )

            distance = output.count("\n") if output else 0

            if returncode == 0 and distance > 0:
                second_round.append((ancestor_candidate, distance))

        def argmin(x):
            return min(range(len(x)), key=lambda i: x[i][1])

        if second_round:
            found_ancestor = second_round[argmin(second_round)][0]

    if found_ancestor is None:
        logger.error("No branch to rebase upon found, specify it with --onto")
        return 1

    for command in build.component.check_branch_commands:
        wrapped_command = f"orc shell bash -c {quote(command)}"
        try:
            run_user_script(
                f"""git rebase -v --reschedule-failed-exec -x {quote(wrapped_command)} {found_ancestor}""",
                cwd=build.install.source_dir,
            )
        except UserException:
            logger.error("Rebase failed!")
            return 1

    logger.info("Success")
    return 0
