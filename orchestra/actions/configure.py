import os
from pathlib import Path

from loguru import logger

from .action import ActionForBuild


class ConfigureAction(ActionForBuild):
    def __init__(self, build, script, config):
        super().__init__("configure", build, script, config)

    def is_satisfied(self):
        # TODO: invalidate configure if self_hash (or even recursive_hash?) has changed
        return os.path.exists(self._configure_successful_path)

    def _run(self):
        if os.path.exists(self._configure_successful_path):
            logger.warning("This component was already successfully configured, rerunning configure script")
            os.remove(self._configure_successful_path)
        elif os.path.exists(self.environment["BUILD_DIR"]):
            logger.warning("Previous configure probably failed, running configure script in a dirty environment")
            logger.warning(f"You might want to delete the build directory "
                           f"(use `orchestra clean {self.build.qualified_name}`)")

        self._run_user_script(self.script)
        Path(self._configure_successful_path).touch()

    @property
    def _configure_successful_path(self):
        return os.path.join(self.environment["BUILD_DIR"], ".configure_successful")

    def _implicit_dependencies(self):
        if self.build.component.clone:
            return {self.build.component.clone}
        else:
            return set()
