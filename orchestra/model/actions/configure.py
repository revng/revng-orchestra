import os

from ...environment import global_env
from .action import Action


class ConfigureAction(Action):
    def __init__(self, build, script, index):
        super().__init__("configure", build, script, index)

    def is_satisfied(self):
        orchestra = global_env(self.index.config)["ORCHESTRA"]
        build_dir = os.path.join(orchestra, "build", self.build.component.name, self.build.name)
        return os.path.exists(build_dir)
