import logging
from typing import Set


class Action:
    def __init__(self, name, build, script, index):
        self.name = name
        self.build = build
        self.script = script
        self.index = index
        self.dependencies: Set[Action] = set()

    def run(self, show_output=False):
        logging.info(f"Executing {self}")
        self._run(show_output=show_output)

    def _run(self, show_output=False):
        raise NotImplementedError()

    def is_satisfied(self):
        raise NotImplementedError()

    @property
    def qualified_name(self):
        return f"{self.build.qualified_name}[{self.name}]"

    @property
    def script_to_run(self):
        raise NotImplementedError()

    def __str__(self):
        return f"Action {self.name} of {self.build.component.name}@{self.build.name}"

    def __repr__(self):
        return f"Action {self.name} of {self.build.component.name}@{self.build.name}"


# TODO
class CleanAction(Action):
    pass
