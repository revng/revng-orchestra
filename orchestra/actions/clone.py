import json
import os.path
import re

from collections import OrderedDict

from .action import ActionForComponent


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

    def is_satisfied(self):
        return os.path.exists(self.environment["SOURCE_DIR"])

    def branches(self):
        # First, check local checkout
        if self.component.from_source:
            source_dir = self.environment["SOURCE_DIR"]
            if os.path.exists(source_dir):
                return self._branches_from_remote(source_dir)

        cache_filepath = os.path.join(self.config.orchestra_dotdir,
                                      "remote_refs_cache.json")

        # Check the cache
        if os.path.exists(cache_filepath):
            with open(cache_filepath, "rb") as f:
                cached_data = json.loads(f.read())
                if self.component.name in cached_data:
                    return cached_data[self.component.name]

        # Check all the remotes
        remotes = [f"{base_url}/{self.repository}"
                   for base_url
                   in self.config.remotes.values()]
        for remote in remotes:
            result = self._branches_from_remote(remote)
            if result:
                # We have a result, cache and return it
                if os.path.exists(cache_filepath):
                    with open(cache_filepath, "rb") as f:
                        cached_data = json.loads(f.read())
                else:
                    cached_data = {}

                cached_data[self.component.name] = result

                # TODO: prevent race condition, if two clone actions run at the same time
                with open(cache_filepath, "w") as f:
                    json.dump(cached_data, f)

                return result

        return None

    def branch(self):
        branches = self.branches()
        if branches:
            for branch in self.config.branches:
                if branch in branches:
                    return branch, branches[branch]

        return None, None

    def _branches_from_remote(self, remote):
        result = self._try_get_script_output(f'git ls-remote -h --refs "{remote}"')

        parse_regex = re.compile(r"(?P<commit>[a-f0-9]*)\W*refs/heads/(?P<branch>.*)")

        return {branch: commit
                for commit, branch
                in parse_regex.findall(result)}

    def environment(self) -> OrderedDict:
        env = super().environment
        env["GIT_SSH_COMMAND"] = "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10"
        return env
