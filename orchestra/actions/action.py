import os.path
from collections import OrderedDict
from typing import Set

from loguru import logger

from .util import run_script
# Only used for type hints, package-relative import not possible due to circular reference
import orchestra.model.configuration


class Action:
    def __init__(self, name, script, config):
        self.name = name
        self.config: "orchestra.model.configuration.Configuration" = config
        self._explicit_dependencies: Set[Action] = set()
        self._script = script

    def run(self, args):
        logger.info(f"Executing {self}")
        if not args.pretend:
            self._run(args)

    def _run(self, args):
        """Executes the action"""
        run_script(self.script, quiet=args.quiet, environment=self.environment)

    @property
    def script(self):
        """Unless _run is overridden, should return the script to run"""
        return self._script

    def add_explicit_dependency(self, dependency):
        self._explicit_dependencies.add(dependency)

    @property
    def dependencies(self):
        return self._explicit_dependencies.union(self._implicit_dependencies())

    @property
    def dependencies_for_hash(self):
        return self._explicit_dependencies.union(self._implicit_dependencies_for_hash())

    def _implicit_dependencies(self):
        return set()

    def _implicit_dependencies_for_hash(self):
        return self._implicit_dependencies()

    def is_satisfied(self):
        """Returns true if the action is satisfied."""
        raise NotImplementedError()

    def can_run(self):
        """Returns true if the action can be run (i.e. all its dependencies are satisfied)"""
        return all(d.is_satisfied() for d in self.dependencies)

    @property
    def environment(self) -> OrderedDict:
        """Returns additional environment variables provided to the script to be run"""
        return self.config.global_env()

    @property
    def _target_name(self):
        raise NotImplementedError("Action subclasses must implement _target_name")

    @property
    def qualified_name(self):
        return self._target_name + f"[{self.name}]"

    @property
    def name_for_info(self):
        return f"{self.name} {self._target_name}"

    @property
    def name_for_graph(self):
        return self.name_for_info

    @property
    def name_for_components(self):
        return self._target_name

    def __str__(self):
        return f"Action {self.name} of {self.name_for_info}"

    def __repr__(self):
        return self.__str__()


class ActionForComponent(Action):
    def __init__(self, name, component, script, config):
        super().__init__(name, script, config)
        self.component = component

    @property
    def environment(self) -> OrderedDict:
        env = super().environment
        env["SOURCE_DIR"] = os.path.join(self.config.sources_dir, self.component.name)
        return env

    @property
    def _target_name(self):
        return self.component.name


class ActionForBuild(ActionForComponent):
    def __init__(self, name, build, script, config):
        super().__init__(name, build.component, script, config)
        self.build = build

    @property
    def environment(self) -> OrderedDict:
        env = super().environment
        env["BUILD_DIR"] = os.path.join(self.config.builds_dir,
                                        self.build.component.name,
                                        self.build.name)
        env["TMP_ROOT"] = os.path.join(env["TMP_ROOTS"], self.build.safe_name)
        return env

    @property
    def _target_name(self):
        return self.build.qualified_name
