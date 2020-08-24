import logging
import os

from ...environment import export_environment, global_env, per_action_env
from .util import run_script, bash_prelude
from .action import Action


class ConfigureAction(Action):
    def __init__(self, build, script, index):
        super().__init__("configure", build, script, index)

    def _run(self, show_output=False):
        result = run_script(self.script_to_run, show_output=show_output)
        if result.returncode != 0:
            logging.error(f"Subprocess exited with exit code {result.returncode}")
            logging.error(f"Script executed: {self.script_to_run}")
            logging.error(f"STDOUT: {result.stdout}")
            logging.error(f"STDERR: {result.stderr}")
            raise Exception("Configure script failed")

    def is_satisfied(self):
        return os.path.exists(self._build_dir())

    @property
    def script_to_run(self):
        env = per_action_env(self)
        script_to_run = bash_prelude
        script_to_run += export_environment(env)
        script_to_run += self.script
        return script_to_run

    def _build_dir(self):
        orchestra = global_env(self.index.config)["ORCHESTRA"]
        return os.path.join(orchestra, "build", self.build.component.name, self.build.name)
