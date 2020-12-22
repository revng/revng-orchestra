import json
import os
import re
from multiprocessing.pool import ThreadPool

from loguru import logger
from tqdm import tqdm

from ..actions.util import get_script_output


class RemoteCache:
    def __init__(self, config, cache_path):
        self.config = config
        self.cache_path = cache_path

        self._cached_local_data = {}

        if os.path.exists(cache_path):
            with open(cache_path) as f:
                self._cached_remote_data = json.load(f)
        else:
            self._cached_remote_data = {}

    def get_branches_for_component(self, component, local_checkout_dir=None, use_cache=True, update_cache_on_disk=True):
        # Try local remote first
        if use_cache and component.name in self._cached_local_data:
            return self._cached_local_data[component.name]

        if local_checkout_dir and os.path.exists(local_checkout_dir):
            result = self._ls_remote(local_checkout_dir)
            self._cached_local_data[component.name] = result
            return result

        # Then query the nonlocal remotes
        if use_cache and component.name in self._cached_remote_data:
            return self._cached_remote_data[component.name]

        remotes = [f"{base_url}/{component.clone.repository}" for base_url in self.config.remotes.values()]
        for remote in remotes:
            result = self._ls_remote(remote)
            if result:
                self._cached_remote_data[component.name] = result
                if update_cache_on_disk:
                    with open(self.cache_path, "w") as f:
                        json.dump(self._cached_remote_data, f)

                return result

        return None

    def rebuild_cache(self, components, parallelism=1):
        self._cached_local_data = {}
        self._cached_remote_data = {}

        progress_bar = tqdm(total=len(components), unit="component")

        def get_branches_with_update(component):
            logger.info(f"Getting branches for {component.name}")
            self.get_branches_for_component(component, update_cache_on_disk=False)
            progress_bar.update()

        map_to_threadpool(get_branches_with_update, components, parallelism=parallelism)

        with open(self.cache_path, "w") as f:
            json.dump(self._cached_remote_data, f)

    @staticmethod
    def _ls_remote(remote):
        env = dict(os.environ)
        env["GIT_SSH_COMMAND"] = "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10"

        result = get_script_output(f'git ls-remote -h --refs "{remote}"', environment=env,
                                   check_returncode=False).decode("utf-8")

        parse_regex = re.compile(r"(?P<commit>[a-f0-9]*)\W*refs/heads/(?P<branch>.*)")

        return {branch: commit
                for commit, branch
                in parse_regex.findall(result)}


def map_to_threadpool(func, args_list, parallelism=4):
    thread_pool = ThreadPool(parallelism)
    thread_pool.map(func, args_list)
    thread_pool.close()
    thread_pool.join()
