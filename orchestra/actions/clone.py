import os.path

from .action import ActionForComponent
from .util import run_script


class CloneAction(ActionForComponent):
    def __init__(self, component, repository, config):
        super().__init__("clone", component, None, config)
        self.repository = repository

    @property
    def script(self):
        clone_cmds = []
        for remote_base_url in self.config.remotes.values():
            clone_cmds.append(f'git clone "{remote_base_url}/{self.repository}" "$SOURCE_DIR"')
        script = " || \\\n  ".join(clone_cmds)
        script += "\n"

        script += 'git -C "$SOURCE_DIR" branch -m orchestra-temporary\n'

        checkout_cmds = []
        for branch in self.config.branches:
            checkout_cmds.append(f'git -C "$SOURCE_DIR" checkout -b "{branch}" "origin/{branch}"')
        checkout_cmds.append("true")
        script += " || \\\n  ".join(checkout_cmds)
        return script

    def _run(self, args):
        """Executes the action"""
        run_script(self.script, quiet=True, environment=self.environment)

    def is_satisfied(self):
        return os.path.exists(self.environment["SOURCE_DIR"])

    def branches(self):
        return self.config.ls_remote_cache.get_branches_for_component(
            self.component,
            local_checkout_dir=self.environment["SOURCE_DIR"]
        )

    def branch(self):
        branches = self.branches()
        if branches:
            for branch in self.config.branches:
                if branch in branches:
                    return branch, branches[branch]

        return None, None
