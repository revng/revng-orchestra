import os.path
from textwrap import dedent

from loguru import logger
from tqdm import tqdm

from ..model.configuration import Configuration
from ..actions.util import run_internal_subprocess, try_run_internal_subprocess


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("update", handler=handle_update, help="Update components")
    cmd_parser.add_argument("--no-config", action="store_true", help="Don't pull orchestra config")


def handle_update(args):
    config = Configuration(use_config_cache=args.config_cache)
    failed_pulls = []
    failed_clones = []

    if not args.no_config:
        logger.info("Updating orchestra configuration")
        if not git_pull(config.orchestra_dotdir):
            failed_pulls.append(f"orchestra configuration ({config.orchestra_dotdir})")

    logger.info("Updating binary archives")
    os.makedirs(config.binary_archives_dir, exist_ok=True)
    for name, url in config.binary_archives_remotes.items():
        binary_archive_path = os.path.join(config.binary_archives_dir, name)
        if os.path.exists(binary_archive_path):
            logger.info(f"Pulling binary archive {name}")
            if not pull_binary_archive(name, config):
                failed_pulls.append(f"Binary archive {name} ({os.path.join(config.binary_archives_dir, name)})")
        else:
            logger.info(f"Trying to clone binary archive from remote {name} ({url})")
            if not clone_binary_archive(name, url, config):
                failed_clones.append(f"Binary archive {name} ({url})!")

    logger.info("Resetting ls-remote cached info")
    ls_remote_cache = os.path.join(config.orchestra_dotdir, "remote_refs_cache.json")
    if os.path.exists(ls_remote_cache):
        os.remove(ls_remote_cache)

    logger.info("Updating ls-remote cached info")
    clonable_components = [component
                           for _, component
                           in config.components.items()
                           if component.clone]
    for component in tqdm(clonable_components, unit="components"):
        logger.info(f"Fetching the latest remote commit for {component.name}")
        _, _ = component.clone.branch()

    to_pull = []
    for _, component in config.components.items():
        if not component.clone:
            continue

        source_path = os.path.join(config.sources_dir, component.name)
        if not os.path.exists(source_path):
            continue

        to_pull.append(component)

    if to_pull:
        logger.info("Updating repositories")
        for component in tqdm(to_pull, unit="components"):
            source_path = os.path.join(config.sources_dir, component.name)
            assert is_git_repo_root(source_path)

            logger.info(f"Pulling {component.name}")
            if not git_pull(source_path):
                failed_pulls.append(f"Repository {component.name}")

    if failed_pulls:
        formatted_failed_pulls = "\n".join([f"  {repo}" for repo in failed_pulls])
        failed_git_pull_suggestion = dedent(f"""
        Could not git pull --ff-only the following repositories:
        {formatted_failed_pulls}

        Suggestions:
            - check your network connection
            - commit your work
            - `git pull --rebase`, to pull remote changes and apply your commits on top
            - `git push` your changes to the remotes
        """)
        logger.error(failed_git_pull_suggestion)

    if failed_clones:
        formatted_failed_clones = "\n".join([f"  {repo}" for repo in failed_clones])
        failed_git_clone_suggestion = dedent(f"""
                Could not clone the following repositories:
                {formatted_failed_clones}

                Suggestions:
                    - check your network connection
                    - check your ssh and git configuration (try manually cloning the repositories)
                """)
        logger.error(failed_git_clone_suggestion)

    if failed_pulls or failed_clones:
        return 1


def clone_binary_archive(name, url, config):
    """Clones a binary archive. Returns a boolean value representing the operation success."""
    binary_archive_path = os.path.join(config.binary_archives_dir, name)
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10"
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    returncode = try_run_internal_subprocess(
        ["git", "clone", url, binary_archive_path],
        environment=env,
    )
    return returncode == 0


def pull_binary_archive(name, config):
    binary_archive_path = os.path.join(config.binary_archives_dir, name)
    # This check is to ensure we are called with the path of an existing binary archive
    # and don't clean/reset orchestra configuration
    if not is_git_repo_root(binary_archive_path):
        raise Exception(f"{binary_archive_path} is not the root of a git repo, aborting")
    # clean removes untracked files
    git_clean(binary_archive_path)
    # reset restores tracked files to their committed version
    git_reset_hard(binary_archive_path)
    return git_pull(binary_archive_path)


def git_clean(directory):
    return run_internal_subprocess(["git", "clean", "-d", "--force"], cwd=directory)


def git_reset_hard(directory, ref="master"):
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    return run_internal_subprocess(
        ["git", "reset", "--hard", ref],
        cwd=directory,
        environment=env
    )


def git_pull(directory):
    """Runs git pull --ff-only on the given directory.
    Returns a boolean value representing the operation success."""
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    returncode = try_run_internal_subprocess(
        ["git", "pull", "--ff-only"],
        environment=env,
        cwd=directory
    )
    return returncode == 0


def is_git_repo_root(directory):
    return os.path.exists(os.path.join(directory, ".git"))
