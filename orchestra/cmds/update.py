import os.path
from textwrap import dedent

from loguru import logger
from tqdm import tqdm

from . import SubCommandParser
from ..actions.util import run_internal_subprocess, try_run_internal_subprocess
from ..exceptions import UserException
from ..gitutils import is_root_of_git_repo
from ..gitutils.lfs import assert_lfs_installed
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd("update", handler=handle_update, help="Update components")
    cmd_parser.add_argument("--no-config", action="store_true", help="Don't pull orchestra config")
    cmd_parser.add_argument("--parallelism", type=int, default=8, help="Maximum parallel processes")


def handle_update(args):
    config = Configuration(use_config_cache=args.config_cache)
    failed_pulls = []
    failed_clones = []

    assert_lfs_installed()

    if not args.no_config:
        logger.info("Updating orchestra configuration")
        if not git_pull(config.orchestra_dotdir):
            failed_pulls.append(f"orchestra configuration ({config.orchestra_dotdir})")

    logger.info("Updating binary archives")
    os.makedirs(config.binary_archives_dir, exist_ok=True)
    progress_bar = tqdm(config.binary_archives_remotes.items(), unit="archives")
    for name, url in progress_bar:
        binary_archive_path = os.path.join(config.binary_archives_dir, name)
        progress_bar.set_postfix_str(f"{name}")
        if os.path.exists(binary_archive_path):
            logger.debug(f"Pulling binary archive {name}")
            if not pull_binary_archive(name, config):
                failed_pulls.append(f"Binary archive {name} ({os.path.join(config.binary_archives_dir, name)})")
        else:
            logger.info(f"Trying to clone binary archive from remote {name} ({url})")
            if not clone_binary_archive(name, url, config):
                failed_clones.append(f"Binary archive {name} ({url})!")

    logger.info("Resetting ls-remote cached info")
    ls_remote_cache = os.path.join(config.cache_dir, "remote_refs_cache.json")
    if os.path.exists(ls_remote_cache):
        os.remove(ls_remote_cache)

    logger.info("Updating ls-remote cached info")
    failed_ls_remotes = config.remote_heads_cache.rebuild_cache(parallelism=args.parallelism)

    to_pull = []
    for clone_action in config.repositories.values():
        if clone_action.source_dir is not None and os.path.exists(clone_action.source_dir):
            to_pull.append(clone_action.source_dir)

    if len(to_pull) > 0:
        logger.info("Updating repositories")
        progress_bar = tqdm(to_pull, unit="components")
        for source_path in progress_bar:
            source_name = os.path.basename(source_path)
            logger.debug(f"Pulling {source_name}")
            progress_bar.set_postfix_str(f"{source_name}")

            if not is_root_of_git_repo(source_path):
                failed_pulls.append(f"Repository {source_name}: Directory {source_path} is not a git repo")
                continue

            if not git_pull(source_path):
                failed_pulls.append(f"Repository {source_name}")

    if failed_pulls:
        formatted_failed_pulls = "\n".join([f"  - {repo}" for repo in failed_pulls])
        # Note: f-strings don't account for indentation, using a template is more practical
        failed_git_pull_template = dedent(
            """
            Could not git pull --ff-only the following repositories:
            {formatted_failed_pulls}

            Suggestions:
                - check your network connection
                - commit your work
                - `git pull --rebase`, to pull remote changes and apply your commits on top
                - `git push` your changes to the remotes
            """
        )
        failed_git_pull_suggestion = failed_git_pull_template.format(formatted_failed_pulls=formatted_failed_pulls)
        logger.error(failed_git_pull_suggestion)

    if failed_clones:
        formatted_failed_clones = "\n".join([f"  - {repo}" for repo in failed_clones])
        # Note: f-strings don't account for indentation, using a template is more practical
        failed_git_clone_template = dedent(
            """
            Could not clone the following repositories:
            {formatted_failed_clones}

            Suggestions:
                - check your network connection
                - check your ssh and git configuration (try manually cloning the repositories)
            """
        )
        failed_git_clone_suggestion = failed_git_clone_template.format(formatted_failed_clones=formatted_failed_clones)
        logger.error(failed_git_clone_suggestion)

    if failed_ls_remotes:
        formatted_failed_ls_remotes = "\n".join([f"  - {repo}" for repo in failed_ls_remotes])
        # Note: f-strings don't account for indentation, using a template is more practical
        failed_git_clone_template = dedent(
            """
            Could not find the following repositories in any remote:
            {formatted_failed_ls_remotes}

            You will not be able to install components that depend on them.
            """
        )
        failed_ls_remote_suggestion = failed_git_clone_template.format(
            formatted_failed_ls_remotes=formatted_failed_ls_remotes
        )
        logger.info(failed_ls_remote_suggestion)

    return 0


def clone_binary_archive(name, url, config):
    """Clones a binary archive. Returns a boolean value representing the operation success."""
    binary_archive_path = os.path.join(config.binary_archives_dir, name)
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10"
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    returncode = try_run_internal_subprocess(
        ["git", "clone", url, binary_archive_path],
        environment=env,
    )
    return returncode == 0


def pull_binary_archive(name, config):
    binary_archive_path = os.path.join(config.binary_archives_dir, name)
    # This check is to ensure we are called with the path of an existing binary archive
    # and don't clean/reset orchestra configuration
    if not is_root_of_git_repo(binary_archive_path):
        raise UserException(f"{binary_archive_path} is not the root of a git repo, aborting")
    # clean removes untracked files
    git_clean(binary_archive_path)
    # reset restores tracked files to their committed version
    git_reset_hard(binary_archive_path, ref="origin/master")
    return git_pull(binary_archive_path)


def git_clean(directory):
    return run_internal_subprocess(["git", "clean", "-d", "--force"], cwd=directory)


def git_reset_hard(directory, ref="master"):
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return run_internal_subprocess(["git", "reset", "--hard", ref], cwd=directory, environment=env)


def git_pull(directory):
    """Runs git pull --ff-only on the given directory.
    Returns a boolean value representing the operation success."""
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    returncode = try_run_internal_subprocess(["git", "pull", "--ff-only"], environment=env, cwd=directory)
    return returncode == 0
