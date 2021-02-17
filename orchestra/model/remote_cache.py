import json
import os
from multiprocessing.pool import ThreadPool

from loguru import logger
from tqdm import tqdm

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
                error_message = f"IO error while reading remote HEADs cache: {cache_path}. " \
                                f"Try running `orchestra update`"
                raise Exception(error_message) from e
            except json.JSONDecodeError as e:
                error_message = f"Error while parsing remote HEADs cache: {cache_path}. " \
                                f"Try removing it and running `orchestra update`"
                raise Exception(error_message) from e
        else:
            logger.warning("The remote HEADs cache does not exist, you should run `orchestra update`")

    def heads(self, component):
        return self._cached_remote_data.get(component.name)

    def rebuild_cache(self, parallelism=1):
        # TODO: outline progress reporting using a callback
        self._cached_remote_data = {}

        clonable_components = list(filter(lambda c: c.clone is not None, self.config.components.values()))

        progress_bar = tqdm(total=len(clonable_components), unit="component")

        def get_branches_with_update(component):
            logger.debug(f"Fetching the latest remote commit for {component.name}")

            remotes = [f"{base_url}/{component.clone.repository}" for base_url in self.config.remotes.values()]
            for remote in remotes:
                result = ls_remote(remote)
                if result:
                    self._cached_remote_data[component.name] = result
                    break

            progress_bar.update()

        map_to_threadpool(get_branches_with_update, clonable_components, parallelism=parallelism)

        with open(self.cache_path, "w") as f:
            json.dump(self._cached_remote_data, f)


def map_to_threadpool(func, args_list, parallelism=4):
    thread_pool = ThreadPool(parallelism)
    thread_pool.map(func, args_list)
    thread_pool.close()
    thread_pool.join()
