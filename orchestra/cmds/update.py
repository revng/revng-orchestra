import os.path
from textwrap import dedent

from loguru import logger
from tqdm import tqdm

from ..actions.util import run_internal_subprocess, try_run_internal_subprocess
from ..model.configuration import Configuration
from ..util import OrchestraException


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("update", handler=handle_update, help="Update components")
    cmd_parser.add_argument("--no-config", action="store_true", help="Don't pull orchestra config")


def handle_update(args):
    config = Configuration(use_config_cache=args.config_cache)
    failed_pulls = []

    if not args.no_config:
        logger.info("Updating orchestra configuration")
        result = git_pull(config.orchestra_dotdir)
        if result.returncode:
            failed_pulls.append(f"orchestra configuration ({config.orchestra_dotdir})")

    logger.info("Updating binary archives")
    os.makedirs(config.binary_archives_dir, exist_ok=True)
    progress_bar = tqdm(config.binary_archives_remotes.items(), unit="archives")
    for name, url in progress_bar:
        binary_archive_path = os.path.join(config.binary_archives_dir, name)
        progress_bar.set_postfix_str(f"{name}")
        if os.path.exists(binary_archive_path):
            logger.debug(f"Pulling binary archive {name}")
            result = pull_binary_archive(name, config)
            if result.returncode:
                failed_pulls.append(f"Binary archive {name} ({os.path.join(config.binary_archives_dir, name)})")
        else:
            logger.info(f"Trying to clone binary archive from remote {name} ({url})")
            clone_binary_archive(name, url, config)

    logger.info("Resetting ls-remote cached info")
    ls_remote_cache = os.path.join(config.orchestra_dotdir, "remote_refs_cache.json")
    if os.path.exists(ls_remote_cache):
        os.remove(ls_remote_cache)

    logger.info("Updating ls-remote cached info")
    clonable_components = [component
                           for _, component
                           in config.components.items()
                           if component.clone]
    progress_bar = tqdm(clonable_components, unit="components")
    for component in progress_bar:
        logger.debug(f"Fetching the latest remote commit for {component.name}")
        progress_bar.set_postfix_str(f"{component.name}")
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
        progress_bar = tqdm(to_pull, unit="components")
        for component in progress_bar:
            source_path = os.path.join(config.sources_dir, component.name)
            assert is_git_repo(source_path)

            logger.debug(f"Pulling {component.name}")
            progress_bar.set_postfix_str(f"{component.name}")
            result = git_pull(source_path)
            if result.returncode:
                failed_pulls.append(f"Repository {component.name}")

    if failed_pulls:
        formatted_failed_pulls = "\n".join([f"  - {repo}" for repo in failed_pulls])
        # Note: f-strings don't account for indentation, using a template is more practical
        failed_git_pull_template = dedent("""
        Could not git pull --ff-only the following repositories:
        {formatted_failed_pulls}

        Suggestions:
            - check your network connection
            - commit your work
            - `git pull --rebase`, to pull remote changes and apply your commits on top
            - `git push` your changes to the remotes
        """)
        failed_git_pull_suggestion = failed_git_pull_template.format(formatted_failed_pulls=formatted_failed_pulls)
        logger.error(failed_git_pull_suggestion)


def pull_binary_archive(name, config):
    binary_archive_path = os.path.join(config.binary_archives_dir, name)
    # This check is to ensure we are called with the path of an existing binary archive
    # and don't clean/reset orchestra configuration
    if not is_git_repo(binary_archive_path):
        raise OrchestraException(f"{binary_archive_path} is not a git repo, aborting")
    # clean removes untracked files
    git_clean(binary_archive_path)
    # reset restores tracked files to their committed version
    git_reset_hard(binary_archive_path)
    result = git_pull(binary_archive_path)
    return result


def clone_binary_archive(name, url, config):
    binary_archive_path = os.path.join(config.binary_archives_dir, name)
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10"
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    result = run_internal_subprocess(
        ["git", "clone", url, binary_archive_path],
        environment=env,
    )
    if result.returncode:
        logger.info(f"Could not clone binary archive from remote {name}!")


def git_clean(directory):
    return run_internal_subprocess(["git", "-C", directory, "clean", "-d", "--force"])


def git_reset_hard(directory, ref="master"):
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    return run_internal_subprocess(
        ["git", "-C", directory, "reset", "--hard", ref],
        environment=env,
    )


def git_pull(directory):
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    result = try_run_internal_subprocess(
        ["git", "-C", directory, "pull", "--ff-only"],
        environment=env,
    )
    return result


def is_git_repo(directory):
    return os.path.exists(os.path.join(directory, ".git"))
