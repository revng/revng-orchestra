import os.path

from .action import ActionForComponent
from .. import gitutils


class CloneAction(ActionForComponent):
    def __init__(self, component, repository, config):
        super().__init__("clone", component, None, config)
        self.repository = repository

    @property
    def script(self):
        script = 'mkdir -p "$(dirname "$SOURCE_DIR")"\n'

        clone_cmds = []
        for remote_base_url in self.config.remotes.values():
            clone_cmds.append(f'git clone "{remote_base_url}/{self.repository}" "$SOURCE_DIR"')
        script += " || \\\n  ".join(clone_cmds)
        script += "\n"

        script += 'git -C "$SOURCE_DIR" branch -m orchestra-temporary\n'

        # Try fetching each remote ref and adding a local branch with the same name that can be checked out
        fetch_cmds = []
        for branch in self.config.branches:
            fetch_cmds.append(
                f'git -C "$SOURCE_DIR" fetch origin "{branch}:{branch}" && git -C "$SOURCE_DIR" checkout "{branch}"'
            )
        fetch_cmds.append("true")

        script += " || \\\n  ".join(fetch_cmds)
        return script

    def is_satisfied(self):
        return os.path.exists(self.environment["SOURCE_DIR"])

    def heads(self):
        """Returns a dictionary of branch names -> commit hash.
        This information is retrieved either from the local clone
        or from the first remote where the repository exists"""
        # Give priority to the local checkout
        source_dir = self.environment["SOURCE_DIR"]
        if os.path.exists(source_dir):
            return gitutils.ls_remote(source_dir)

        return self.config.remote_heads_cache.heads(self.component)

    def branch(self):
        """Returns a 2-tuple (branch name, commit hash).
        If a local clone exists the information regards the currently checked out branch,
        otherwise it is taken from the configured remotes.
        """
        source_dir = self.environment["SOURCE_DIR"]
        if gitutils.is_root_of_git_repo(source_dir):
            return gitutils.current_branch_info(source_dir)

        branches = self.heads()
        if branches:
            for branch in self.config.branches:
                if branch in branches:
                    return branch, branches[branch]

        return None, None
