import logging
from collections import OrderedDict
from typing import Set

from .util import run_script


class Action:
    def __init__(self, name, build, script, config):
        self.name = name
        self.build = build
        self.config = config
        self.external_dependencies: Set[Action] = set()
        self._script = script

    def run(self, show_output=False, args=None):
        logging.info(f"Executing {self}")
        self._run(show_output=show_output, args=args)

    def _run(self, show_output=False, args=None):
        """Executes the action"""
        run_script(self.script, show_output=show_output, environment=self.environment)

    @property
    def script(self):
        """Unless _run is overridden, should return the script to run"""
        return self._script

    @property
    def dependencies(self):
        return self.external_dependencies.union(self._implicit_dependencies())

    def _implicit_dependencies(self):
        return set()

    def is_satisfied(self, recursively=False, already_checked=None):
        if already_checked is None:
            already_checked = set()

        if not self._is_satisfied():
            return False

        elif not recursively:
            return True
        else:
            already_checked.add(self)
            for d in self.dependencies:
                if d in already_checked:
                    continue
                d_satisfied = d.is_satisfied(recursively=recursively, already_checked=already_checked)
                if not d_satisfied:
                    return False
            return True

    def _is_satisfied(self):
        """Returns true if the action is satisfied, false if it needs to run."""
        raise NotImplementedError()

    @property
    def environment(self) -> OrderedDict:
        """Returns additional environment variables provided to the script to be run"""
        env = self.config.global_env()
        env["SOURCE_DIR"] = f"""{self.config.sources_dir}/{self.build.component.name}"""
        env["BUILD_DIR"] = f"""{self.config.builds_dir}/{self.build.component.name}/{self.build.name}"""
        return env

    @property
    def qualified_name(self):
        return f"{self.build.qualified_name}[{self.name}]"

    @property
    def name_for_graph(self):
        return f"{self.name} {self.build.component.name}@{self.build.name}"

    @property
    def name_for_components(self):
        return f"{self.build.qualified_name}"

    def __str__(self):
        return f"Action {self.name} of {self.build.component.name}@{self.build.name}"

    def __repr__(self):
        return f"Action {self.name} of {self.build.component.name}@{self.build.name}"
