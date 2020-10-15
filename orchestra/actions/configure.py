import os

from loguru import logger

from .action import Action
from .util import run_script


class ConfigureAction(Action):
    def __init__(self, build, script, config):
        super().__init__("configure", build, script, config)

    def _is_satisfied(self):
        return os.path.exists(self._configure_successful_path)

    def _run(self, args):
        if os.path.exists(self._configure_successful_path):
            logger.warning("This component was already successfully configured, rerunning configure script")
            os.remove(self._configure_successful_path)
        elif os.path.exists(self.environment["BUILD_DIR"]):
            logger.warning("Previous configure probably failed, running configure script in a dirty environment")
            logger.warning(f"You might want to delete the build directory (use `orchestra clean`)")

        result = run_script(self.script, quiet=args.quiet, environment=self.environment)
        if result.returncode == 0:
            open(self._configure_successful_path, "w").close()

    @property
    def _configure_successful_path(self):
        return os.path.join(self.environment["BUILD_DIR"], ".configure_successful")

    def _implicit_dependencies(self):
        if self.build.clone:
            return {self.build.clone}
        else:
            return set()
