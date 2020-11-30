import json
import os.path
import re

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
        for branch in self.branches():
            checkout_cmds.append(f'git -C "$SOURCE_DIR" checkout -b "{branch}" "origin/{branch}"')
        checkout_cmds.append("true")
        script += " || \\\n  ".join(checkout_cmds)
        return script

    def _run(self, args):
        """Executes the action"""
        run_script(self.script, quiet=True, environment=self.environment)

    def _is_satisfied(self):
        return os.path.exists(self.environment["SOURCE_DIR"])

    @staticmethod
    def branches():
        return ["develop", "master"]

    def get_remote_head(self):
        # First, check local checkout
        if self.component.from_source:
            source_dir = self.environment["SOURCE_DIR"]
            if os.path.exists(source_dir):
                result = self._ls_remote(self.environment["SOURCE_DIR"])
                branch, commit = self._commit_from_ls_remote(result)
                if commit:
                    return branch, commit

        cache_filepath = os.path.join(self.config.orchestra_dotdir, "remote_refs_cache.json")

        if os.path.exists(cache_filepath):
            with open(cache_filepath, "rb") as f:
                cached_data = json.loads(f.read())
                if self.component.name in cached_data:
                    return tuple(cached_data[self.component.name])

        remotes = [f"{base_url}/{self.repository}"
                   for base_url
                   in self.config.remotes.values()]
        for remote in remotes:
            result = self._ls_remote(remote)

            branch, commit = self._commit_from_ls_remote(result)

            if result:
                if os.path.exists(cache_filepath):
                    with open(cache_filepath, "rb") as f:
                        cached_data = json.loads(f.read())
                else:
                    cached_data = {}

                cached_data[self.component.name] = [branch, commit]
                # TODO: prevent race condition, if two clone actions run at the same time
                with open(cache_filepath, "w") as f:
                    json.dump(cached_data, f)

            if commit:
                return branch, commit
        return None, None

    def _commit_from_ls_remote(self, result):
        parse_regex = re.compile(r"(?P<commit>[a-f0-9]*)\W*refs/heads/(?P<branch>.*)")
        remote_branches = {branch: commit
                           for commit, branch
                           in parse_regex.findall(result)}
        for branch in self.branches():
            if branch in remote_branches:
                return branch, remote_branches[branch]
        return None, None

    def _ls_remote(self, remote):
        env = dict(self.environment)
        env["GIT_SSH_COMMAND"] = "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10"
        data = run_script(
            f'git ls-remote -h --refs "{remote}"',
            quiet=True,
            environment=env,
            check_returncode=False
        ).stdout.decode("utf-8")

        return data
