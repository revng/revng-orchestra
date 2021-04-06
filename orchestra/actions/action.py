import os.path
from collections import OrderedDict
from typing import Set

from loguru import logger

# Only used for type hints, package-relative import not possible due to circular reference
import orchestra.model.configuration
from .util import run_user_script, run_internal_script, get_script_output
from .util import try_run_internal_script, try_get_script_output


class Action:
    def __init__(self, name, script, config):
        self.name = name
        self.config: "orchestra.model.configuration.Configuration" = config
        self._explicit_dependencies: Set[Action] = set()
        self._script = script

    def run(self, pretend=False, explicitly_requested=False):
        logger.info(f"Executing {self}")
        if not pretend:
            self._run(explicitly_requested=explicitly_requested)

    def _run(self, explicitly_requested=False):
        """Executes the action"""
        self._run_user_script(self.script)

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

    @property
    def environment(self) -> "OrderedDict[str, str]":
        """Returns additional environment variables provided to the script to be run"""
        return self.config.global_env()

    @property
    def _target_name(self):
        raise NotImplementedError("Action subclasses must implement _target_name")

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
        return f"Action {self.name} of {self._target_name}"

    def __repr__(self):
        return self.__str__()

    def _run_user_script(self, script, cwd=None):
        run_user_script(script, environment=self.environment, cwd=cwd)

    def _run_internal_script(self, script, cwd=None):
        run_internal_script(script, environment=self.environment, cwd=cwd)

    def _try_run_internal_script(self, script, cwd=None):
        return try_run_internal_script(script, environment=self.environment, cwd=cwd)

    def _get_script_output(self, script, cwd=None):
        return get_script_output(script, environment=self.environment, cwd=cwd)

    def _try_get_script_output(self, script, cwd=None):
        return try_get_script_output(script, environment=self.environment, cwd=cwd)


class ActionForComponent(Action):
    def __init__(self, name, component, script, config):
        super().__init__(name, script, config)
        self.component = component

    @property
    def environment(self) -> "OrderedDict[str, str]":
        env = super().environment
        env["SOURCE_DIR"] = self.source_dir
        return env

    @property
    def _target_name(self):
        return self.component.name

    @property
    def source_dir(self) -> str:
        return os.path.join(self.config.sources_dir, self.component.name)


class ActionForBuild(ActionForComponent):
    def __init__(self, name, build, script, config):
        super().__init__(name, build.component, script, config)
        self.build = build

    @property
    def environment(self) -> "OrderedDict[str, str]":
        env = super().environment
        env["BUILD_DIR"] = self.build_dir
        env["TMP_ROOT"] = self.tmp_root
        return env

    @property
    def build_dir(self) -> str:
        return os.path.join(self.config.builds_dir, self.build.component.name, self.build.name)

    @property
    def tmp_root(self) -> str:
        return os.path.join(super().environment["TMP_ROOTS"], self.build.safe_name)

    @property
    def _target_name(self):
        return self.build.qualified_name
