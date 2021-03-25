import json
import re
from itertools import repeat
from typing import Union

from . import component as comp
from ._hash import hash
from ..actions import any_of
from ..actions import configure
from ..actions import install


class Build:
    def __init__(
            self,
            name: str,
            serialized_build,
            component: 'comp.Component',
            configuration,
    ):
        self.name = name
        self.component: comp.Component = component

        self.ndebug = serialized_build.get("ndebug", True)

        configure_script = serialized_build["configure"]
        self.configure = configure.ConfigureAction(self, configure_script, configuration)

        install_script = serialized_build["install"]
        force_build = component.build_from_source or configuration.build_all_from_source
        allow_build = configuration.fallback_to_build or force_build
        allow_binary_archive = not force_build
        self.install = install.InstallAction(
            self,
            install_script,
            configuration,
            allow_build=allow_build,
            allow_binary_archive=allow_binary_archive,
            create_binary_archive=configuration.create_binary_archives,
            no_merge=configuration.no_merge,
            keep_tmproot=configuration.keep_tmproot,
            run_tests=configuration.run_tests,
        )

        # Dependency names are needed for resolving them to the actual Actions and to compute the build hash
        self._explicit_dependencies = serialized_build.get("dependencies", [])
        self._explicit_build_dependencies = serialized_build.get("build_dependencies", [])

        self.build_hash = self._compute_build_hash()

        self._resolve_dependencies_called = False

    def resolve_dependencies(self, configuration):
        if self._resolve_dependencies_called:
            raise Exception("Called resolve_dependencies twice")
        self._resolve_dependencies_called = True

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
                alternatives = {b.install for b in dep_component.builds.values()}
                dependency_action = any_of.AnyOfAction(alternatives, preferred_build.install)
            else:
                dependency_action = preferred_build.install

            self.configure.add_explicit_dependency(dependency_action)
            if not build_only:
                self.install.add_explicit_dependency(dependency_action)

    @property
    def qualified_name(self):
        return f"{self.component.name}@{self.name}"

    @property
    def safe_name(self):
        return self.qualified_name.replace("@", "_").replace("/", "_")

    def serialize(self):
        return {
            "configure": self.configure.script,
            "install": self.install.script,
            "dependencies": self._explicit_dependencies,
            "build_dependencies": self._explicit_build_dependencies,
            "ndebug": self.ndebug
        }

    def _compute_build_hash(self):
        return hash(json.dumps(self.serialize(), sort_keys=True))

    def __str__(self):
        return f"Build {self.component.name}@{self.name}"

    def __repr__(self):
        return f"Build {self.component.name}@{self.name}"


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
