import os
import re
from pathlib import Path
from typing import Optional, Union
from loguru import logger


from ..actions.util import get_subprocess_output, run_internal_subprocess
from ..exceptions import InternalException, InternalCommandException


def _only(elements):
    assert len(elements) == 1
    return elements[0]


def _clean_env(env=None):
    if not env:
        env = os.environ
    return {k: v for k, v in env.items() if k != "GIT_DIR"}


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
    dot_git = Path(repo_path) / ".git"

    # If it's a file, open it and move there
    if dot_git.is_file():
        content = dot_git.read_text().strip()
        dot_git = Path(re.search(r"(?<=gitdir: ).*", content)[0])

    # At this point dot_git is a directory
    assert dot_git.is_dir()

    # Read HEAD
    head = (dot_git / "HEAD").read_text().strip()

    # Are we on a branch?
    match = re.match("ref: refs/heads/(.*)", head)
    if not match:
        # Deatached head
        return "HEAD", head
    branch = match[1]

    # If we have a commondir file, move there
    commondir_path = dot_git / "commondir"
    if commondir_path.is_file():
        commondir = Path(commondir_path.read_text().strip())
        if not commondir.is_absolute():
            commondir = dot_git / commondir
        dot_git = commondir

    # Look into .git/refs/heads/$BRANCH_NAME
    branch_file = dot_git / "refs" / "heads" / branch
    if branch_file.is_file():
        commit = branch_file.read_text().strip()
    else:
        # Look into .git/info/refs
        refs = (dot_git / "info" / "refs").read_text().strip()
        commit = _only(
            [
                match[1]
                for match in [
                    re.match(rf"^([0-9a-f]*)\s+refs/heads/{branch}$", line.strip()) for line in refs.split("\n")
                ]
                if match
            ]
        )

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
