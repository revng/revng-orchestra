import json
import os
from concurrent.futures import ThreadPoolExecutor

from loguru import logger
from tqdm import tqdm

from ..exceptions import UserException
from ..gitutils import ls_remote


class RemoteHeadsCache:
    def __init__(self, config, cache_path):
        self.config = config
        self.cache_path = cache_path

        self._cached_remote_data = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    self._cached_remote_data = json.load(f)
            except IOError as e:
                error_message = (
                    f"IO error while reading remote HEADs cache: {cache_path}. Try running `orchestra update`"
                )
                raise UserException(error_message) from e
            except json.JSONDecodeError as e:
                error_message = (
                    f"Error while parsing remote HEADs cache: {cache_path}. "
                    f"Try removing it and running `orchestra update`"
                )
                raise UserException(error_message) from e
        else:
            logger.warning("The remote HEADs cache does not exist, you should run `orchestra update`")

    def heads(self, component):
        return self._cached_remote_data.get(component.name)

    def rebuild_cache(self, parallelism=1):
        # TODO: outline progress reporting using a callback
        self._cached_remote_data = {}

        clonable_components = list(filter(lambda c: c.clone is not None, self.config.components.values()))

        def get_branches(component):
            logger.debug(f"Fetching the latest remote commit for {component.name}")

            remotes = [f"{base_url}/{component.clone.repository}" for base_url in self.config.remotes.values()]
            result = None
            for remote in remotes:
                result = ls_remote(remote)
                if result:
                    self._cached_remote_data[component.name] = result
                    break

            if not result:
                return component.clone.repository

        failed_repositories = []
        progress_bar = tqdm(total=len(clonable_components), unit="component")
        with ThreadPoolExecutor(max_workers=parallelism) as executor:
            for failed_repository in executor.map(get_branches, clonable_components):
                if failed_repository is not None:
                    failed_repositories.append(failed_repository)
                progress_bar.update()

        self._persist_cache()
        return failed_repositories

    def _persist_cache(self):
        with open(self.cache_path, "w") as f:
            json.dump(self._cached_remote_data, f)

    def set_entry(self, component_name, branch_name, commit):
        """Sets a cache entry and persists the cache to disk. Not thread safe!"""
        current_cached_info = self._cached_remote_data.get(component_name, {})
        current_cached_info[branch_name] = commit
        self._cached_remote_data[component_name] = current_cached_info
        self._persist_cache()
