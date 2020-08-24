import logging
import os.path

from .action import Action
from ...environment import export_environment, per_action_env
from .util import bash_prelude, run_script


class CloneAction(Action):
    def __init__(self, build, repository, index):
        script = f'clone "{repository}"'
        super().__init__("clone", build, script, index)
        self.repository = repository

    def _run(self, show_output=False):
        result = run_script(self.script_to_run, show_output=show_output)
        if result.returncode != 0:
            logging.error(f"Subprocess exited with exit code {result.returncode}")
            logging.error(f"Script executed: {self.script_to_run}")
            logging.error(f"STDOUT: {result.stdout}")
            logging.error(f"STDERR: {result.stderr}")
            raise Exception("Clone script failed")

    def is_satisfied(self):
        source_dir = per_action_env(self)["SOURCE_DIR"]
        return os.path.exists(source_dir)

    @property
    def script_to_run(self):
        script = bash_prelude
        script += export_environment(per_action_env(self))

        clone_cmds = []
        for remote_base_url in self.remote_base_urls():
            clone_cmds.append(f"""git clone "{remote_base_url}/{self.repository}" "$SOURCE_DIR" """)
        script += "|| \\\n  ".join(clone_cmds)

        script += """\ngit -C "$SOURCE_DIR" branch -m orchestra-temporary\n"""

        checkout_cmds = []
        for branch in self.branches():
            checkout_cmds.append(f"""git -C "$SOURCE_DIR" checkout -b "{branch}" "origin/{branch}" """)
        checkout_cmds.append("true")
        script += " || \\\n  ".join(checkout_cmds)
        return script

    @staticmethod
    def remote_base_urls():
        # TODO: the remote is not necessarily called origin, and there might be more than one
        #  remote names should be configurable
        remotes = ["origin"]
        base_urls = []

        for remote in remotes:
            remote_url = run_script(f"""git -C "$ORCHESTRA" config --get remote.{remote}.url""").stdout.strip().decode("utf-8")
            remote_base_url = run_script(f"""dirname "{remote_url}" """).stdout.strip().decode("utf-8")
            base_urls.append(remote_base_url)

        return base_urls

    @staticmethod
    def branches():
        return ["develop", "master"]
