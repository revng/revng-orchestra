import os
import re

from ..actions.util import get_subprocess_output, try_get_subprocess_output
from ..util import OrchestraException


def ls_remote(remote):
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10"
    env["GIT_ASKPASS"] = "/bin/true"
    result = try_get_subprocess_output(["git", "ls-remote", "-h", "--refs", remote], environment=env)
    if result is None:
        return {}

    parse_regex = re.compile(r"(?P<commit>[a-f0-9]*)\W*refs/heads/(?P<branch>.*)")

    return {branch: commit
            for commit, branch
            in parse_regex.findall(result)}


def current_branch_info(repo_path):
    try:
        branch_name = get_subprocess_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path).strip()
        commit = get_subprocess_output(["git", "rev-parse", "HEAD"], cwd=repo_path).strip()
        return branch_name, commit
    except OrchestraException:
        return None, None


def is_root_of_git_repo(path):
    """Returns true if the given path is the root of a git repository (it contains a .git directory)"""
    return os.path.exists(path) and ".git" in os.listdir(path)
