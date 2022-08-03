import os
import re
from pathlib import Path
from typing import Optional, Union
from loguru import logger


from ..actions.util import get_subprocess_output, run_internal_subprocess
from ..exceptions import InternalException, InternalCommandException

def _clean_env(env=None):
    if not env:
        env = os.environ

    env = env.copy()

    if "GIT_DIR" in env:
        del env["GIT_DIR"]

    return env

def run_git(
    *args,
    workdir: Optional[Union[str, Path]] = None,
):
    """Run a git command. Raises an InternalSubprocessException if git returns a non-zero exit code.
    :param workdir: Git behaves as if it was invoked in this working directory (optional)
    """
    git_cmd = [
        "git",
    ]
    if workdir:
        git_cmd.append("-C")
        git_cmd.append(str(workdir))
    git_cmd.extend(args)

    return run_internal_subprocess(git_cmd, environment=_clean_env())


def ls_remote(remote):
    env = _clean_env()
    try:
        result = get_subprocess_output(["git", "ls-remote", "-h", "--refs", remote], environment=env)
    except InternalCommandException:
        return {}

    parse_regex = re.compile(r"(?P<commit>[a-f0-9]*)\W*refs/heads/(?P<branch>.*)")

    return {branch: commit for commit, branch in parse_regex.findall(result)}


def current_branch_info(repo_path):
    # Compute base .git path
    dot_git = os.path.join(repo_path, ".git")

    # If it's a file, open it and move there
    if os.path.isfile(dot_git):
        with open(dot_git, "r") as dot_git_file:
            content = dot_git_file.read().strip()
        dot_git = re.match("""gitdir: (.*)""", content).groups()[0]

    # At this point dot_git is a directory
    assert os.path.isdir(dot_git)

    # Read HEAD
    with open(os.path.join(dot_git, "HEAD"), "r") as head_file:
        head = head_file.read().strip()

    # Are we on a branch?
    match = re.match("ref: refs/heads/(.*)", head)
    if not match:
        return None, None
    branch = match.groups()[0]

    # If we have a commondir file, move there
    commondir_path = os.path.join(dot_git, "commondir")
    if os.path.isfile(commondir_path):
        with open(commondir_path, "r") as commondir_file:
            commondir = commondir_file.read().strip()
            if not os.path.isabs(commondir):
                commondir = os.path.join(dot_git, commondir)
            dot_git = commondir

    # Open the file containing the branch name
    with open(os.path.join(dot_git, "refs", "heads", branch), "r") as ref_file:
        commit = ref_file.read().strip()

    return branch, commit


def is_root_of_git_repo(path):
    """Returns true if the given path is the root of a git repository (it contains a .git directory)"""
    return os.path.exists(path) and ".git" in os.listdir(path)


def get_worktree_root(absolute_path_to_file_in_worktree: Union[str, Path]) -> Path:
    """Returns the root of a git worktree given the absolute path to a file in the worktree.
    The worktree must be a "canonical" clone, e.g. the root is the directory containing the .git repository directory"""
    absolute_path_to_file_in_worktree = Path(absolute_path_to_file_in_worktree)
    assert absolute_path_to_file_in_worktree.is_absolute()
    root_path = Path("/")
    while absolute_path_to_file_in_worktree != root_path:
        if (absolute_path_to_file_in_worktree / ".git").exists():
            return absolute_path_to_file_in_worktree
        absolute_path_to_file_in_worktree = absolute_path_to_file_in_worktree.parent

    # Edge case: the root contains the git repo
    if (absolute_path_to_file_in_worktree / ".git").exists():
        return absolute_path_to_file_in_worktree

    raise InternalException(f"{absolute_path_to_file_in_worktree} is not inside a git worktree")
