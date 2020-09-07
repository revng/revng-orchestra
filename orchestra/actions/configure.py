import os

from .action import Action


class ConfigureAction(Action):
    def __init__(self, build, script, config):
        super().__init__("configure", build, script, config)

    def _is_satisfied(self):
        return os.path.exists(self.environment["BUILD_DIR"])

    def _implicit_dependencies(self):
        if self.build.clone:
            return {self.build.clone}
        else:
            return set()
