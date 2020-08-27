import logging
from collections import OrderedDict
from typing import Set

from .util import run_script
from ...environment import per_action_env


class Action:
    def __init__(self, name, build, script, index):
        self.name = name
        self.build = build
        self.index = index
        self.dependencies: Set[Action] = set()
        self._script = script

    def run(self, show_output=False):
        logging.info(f"Executing {self}")
        self._run(show_output=show_output)

    def _run(self, show_output=False):
        """Executes the action"""
        run_script(self.script, show_output=show_output, environment=self.environment)

    @property
    def script(self):
        """Unless _run is overridden, should return the script to run"""
        return self._script

    def is_satisfied(self):
        raise NotImplementedError()

    @property
    def environment(self) -> OrderedDict:
        """Returns additional environment variables provided to the script to be run"""
        return per_action_env(self)

    @property
    def qualified_name(self):
        return f"{self.build.qualified_name}[{self.name}]"

    def __str__(self):
        return f"Action {self.name} of {self.build.component.name}@{self.build.name}"

    def __repr__(self):
        return f"Action {self.name} of {self.build.component.name}@{self.build.name}"


# TODO
class CleanAction(Action):
    pass
