import os.path

from .action import Action
from .util import run_script


class CloneAction(Action):
    def __init__(self, build, repository, config):
        super().__init__("clone", build, None, config)
        self.repository = repository

    @property
    def script(self):
        clone_cmds = []
        for remote_base_url in self.remote_base_urls():
            clone_cmds.append(f'git clone "{remote_base_url}/{self.repository}" "$SOURCE_DIR"')
        script = " || \\\n  ".join(clone_cmds)
        script += "\n"

        script += 'git -C "$SOURCE_DIR" branch -m orchestra-temporary\n'

        checkout_cmds = []
        for branch in self.branches():
            checkout_cmds.append(f'git -C "$SOURCE_DIR" checkout -b "{branch}" "origin/{branch}"')
        checkout_cmds.append("true")
        script += " || \\\n  ".join(checkout_cmds)
        return script

    def _is_satisfied(self):
        return os.path.exists(self.environment["SOURCE_DIR"])

    def remote_base_urls(self):
        # TODO: the remote is not necessarily called origin, and there might be more than one
        #  remote names should be configurable
        remotes = ["origin", "private"]
        base_urls = []

        for remote in remotes:
            result = run_script(
                f'git -C "$ORCHESTRA_DOTDIR" config --get remote.{remote}.url',
                environment=self.environment
            )
            remote_url = result.stdout.strip().decode("utf-8")
            remote_base_url = remote_url.rpartition("/")[0]
            base_urls.append(remote_base_url)

        return base_urls

    @staticmethod
    def branches():
        return ["develop", "master"]
