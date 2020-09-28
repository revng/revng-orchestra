import json
import os.path
import re
from functools import lru_cache

from .action import Action
from .util import run_script


class CloneAction(Action):
    def __init__(self, build, repository, config):
        super().__init__("clone", build, None, config)
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

    def _is_satisfied(self):
        return os.path.exists(self.environment["SOURCE_DIR"])

    @staticmethod
    def branches():
        return ["develop", "master"]

    @lru_cache()
    def get_remote_head(self):
        remotes = [f"{base_url}/{self.repository}" for base_url in self.config.remotes.values()]
        local_repo = os.path.join(self.environment["SOURCE_DIR"], ".git")
        if os.path.exists(local_repo):
            remotes.insert(0, local_repo)

        for remote in remotes:
            result = self._ls_remote(remote)
            parse_regex = re.compile(r"(?P<commit>[a-f0-9]*)\W*refs/heads/(?P<branch>.*)")
            matches = parse_regex.findall(result)
            for commit, branch in matches:
                if branch in self.branches():
                    return commit
        return None

    @lru_cache()
    def _ls_remote(self, remote):
        cache_filepath = os.path.join(self.config.orchestra_dotdir, "remote_refs_cache.json")

        if os.path.exists(cache_filepath):
            with open(cache_filepath, "rb") as f:
                cached_data = json.loads(f.read())
                if self.build.qualified_name in cached_data:
                    return cached_data[self.build.qualified_name]

        data = run_script(
            f'git ls-remote -h --refs "{remote}"',
            quiet=True,
            environment=self.environment,
            check_returncode=False
        ).stdout.decode("utf-8")

        if os.path.exists(cache_filepath):
            with open(cache_filepath, "rb") as f:
                cached_data = json.loads(f.read())
        else:
            cached_data = {}

        cached_data[self.build.qualified_name] = data
        # TODO: prevent race condition, if two clone actions run at the same time
        with open(cache_filepath, "w") as f:
            json.dump(cached_data, f)

        return data
