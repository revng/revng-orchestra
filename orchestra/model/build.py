from enum import Enum, auto
from itertools import repeat
from typing import Union
import hashlib
import json
import os.path
import re

from . import component
from ..actions import ConfigureAction
from ..actions import InstallAction
from ..actions import AnyOfAction


class Build:
    def __init__(
            self,
            name: str,
            serialized_build,
            comp: 'component.Component',
            configuration,
    ):
        self.name = name
        self.component: component.Component = comp

        self.ndebug = serialized_build.get("ndebug", True)
        self.test = serialized_build.get("test", False)

        self.build_hash = self._compute_build_hash(serialized_build)

        self.__build_state = BuildState.NOT_READY

        configure_script = serialized_build["configure"]
        self.configure = ConfigureAction(self, configure_script, configuration)

        install_script = serialized_build["install"]
        force_build = serialized_build.get("build_from_source", False) or configuration.build_all_from_source
        allow_build = configuration.fallback_to_build or force_build
        allow_binary_archive = not force_build
        self.install = InstallAction(
            self,
            install_script,
            configuration,
            allow_build=allow_build,
            allow_binary_archive=allow_binary_archive,
            create_binary_archive=configuration.create_binary_archives,
        )

        # -- Save dependencies in string form for resolving them later
        self._explicit_dependencies = serialized_build.get("dependencies", [])
        self._explicit_build_dependencies = serialized_build.get("build_dependencies", [])

    def resolve_dependencies(self, configuration):
        if self.__build_state is not BuildState.NOT_READY:
            raise Exception("Called resolve_dependencies at the wrong time")

        # List of (dependency_name: str, build_only: bool)
        all_explicit_dependencies = []
        all_explicit_dependencies += list(zip(self._explicit_dependencies, repeat(False)))
        all_explicit_dependencies += list(zip(self._explicit_build_dependencies, repeat(True)))

        for dependency_name, build_only in all_explicit_dependencies:
            dep_component_name, dep_build_name, exact_build_required = parse_dependency(dependency_name)
            dep_component = configuration.components[dep_component_name]

            if dep_build_name:
                preferred_build = dep_component.builds[dep_build_name]
            else:
                preferred_build = dep_component.default_build

            if not exact_build_required:
                alternatives = [b.install for b in dep_component.builds.values()]
                dependency_action = AnyOfAction(alternatives, preferred_build.install)
            else:
                dependency_action = preferred_build.install

            self.configure.add_explicit_dependency(dependency_action)
            if not build_only:
                self.install.add_explicit_dependency(dependency_action)

        del self._explicit_dependencies
        del self._explicit_build_dependencies

        self.__build_state = BuildState.READY

    @property
    def qualified_name(self):
        return f"{self.component.name}@{self.name}"

    @property
    def safe_name(self):
        return self.qualified_name.replace("@", "_").replace("/", "_")

    @property
    def binary_archive_dir(self):
        """Returns the relative dirname where the binary archives should be created/found."""
        return os.path.join(self.component.name, self.name)

    @property
    def binary_archive_filename(self):
        """Returns the filename of the binary archive. Remember to os.path.join it with binary_archive_dir!"""
        component_commit = self.component.commit() or "none"
        return f'{component_commit}_{self.component.recursive_hash}.tar.gz'

    @staticmethod
    def _compute_build_hash(serialized_build):
        return hashlib.sha1(json.dumps(serialized_build, sort_keys=True).encode("utf-8")).hexdigest()

    def __str__(self):
        return f"Build {self.component.name}@{self.name}"

    def __repr__(self):
        return f"Build {self.component.name}@{self.name}"


class BuildState(Enum):
    NOT_READY = auto()
    READY = auto()


def parse_dependency(dependency) -> (str, Union[str, None], bool):
    """
    Dependencies can be specified in the following formats:
    - Simple:
        `component`
        Depend on the installation of the default build of `component`.
    - Exact:
        `component@build`
        Depend on the installation of a specific build of `component`
    - Simple with preferred build:
        `component~build`
        to depend on the installation of any build of `component`.
        If the component is not installed, the specified build is picked.

    :returns component_name, build_name, exact_build_required
                component_name: name of the requested component
                build_name: name of the requested build or None
                exact_build_required: True if build_name represents an exact requirement
    """
    dependency_re = re.compile(r"(?P<component>[\w\-_/]+)((?P<type>[@~])(?P<build>[\w\-_/]+))?")
    match = dependency_re.fullmatch(dependency)
    if not match:
        raise Exception(f"Invalid dependency specified: {dependency}")

    component = match.group("component")
    exact_build_required = False if match.group("type") == "~" else True
    build = match.group("build")

    return component, build, exact_build_required
