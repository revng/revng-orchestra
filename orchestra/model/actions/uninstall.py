import logging
import os

from ...environment import global_env
from ...util import install_component_path, is_installed
from .action import Action


class UninstallAction(Action):
    def __init__(self, build, index):
        super().__init__("uninstall", build, "", index)

    def _run(self, show_output=False):
        index_path = install_component_path(self.build.component.name, self.index.config)
        with open(index_path) as f:
            f.readline()
            paths = f.readlines()
        paths.sort(reverse=True)
        paths = [path.strip() for path in paths]

        for path in paths:
            path_to_delete = f"{global_env(self.index.config)['ORCHESTRA_ROOT']}/{path}"
            if os.path.isfile(path_to_delete):
                logging.debug(f"Deleting {path_to_delete}")
                continue
                os.remove(path_to_delete)
            elif os.path.isdir(path_to_delete):
                if os.listdir(path_to_delete):
                    logging.debug(f"Not removing directory {path_to_delete} as it is not empty")
                else:
                    logging.debug(f"Deleting directory {path_to_delete}")
                    continue
                    os.rmdir(path_to_delete)

    def is_satisfied(self):
        return not is_installed(self.index.config, self.build.component.name, wanted_build=self.build.name)

    @property
    def script_to_run(self):
        return ""
