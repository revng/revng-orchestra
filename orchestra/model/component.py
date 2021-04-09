from typing import Dict, Set, Union

from . import build as bld
from ._hash import hash
from ..actions import any_of
from ..actions import clone


class Component:
    def __init__(self, name: str, serialized_component, configuration):
        self.name = name
        self.builds: Dict[str, bld.Build] = {}
        self.skip_post_install = serialized_component.get("skip_post_install", False)
        self.license = serialized_component.get("license")
        self.binary_archives = serialized_component.get("binary_archives")
        self.build_from_source = serialized_component.get("build_from_source", False)
        self.add_to_path = serialized_component.get("add_to_path", [])
        self.repository = serialized_component.get("repository")
        self._recursive_hash = None

        self.clone: Union[clone.CloneAction, None] = None
        if self.repository:
            self.clone = clone.CloneAction(self, self.repository, configuration)

        # The default build is either specified, or the first in alphabetical order
        default_build_name = serialized_component.get("default_build")
        if default_build_name is None:
            default_build_name = sorted(serialized_component["builds"])[0]

        if default_build_name not in serialized_component["builds"]:
            raise Exception(f'Invalid default build "{default_build_name}" for component {name}')

        for build_name, build_yaml in serialized_component["builds"].items():
            build = bld.Build(build_name, build_yaml, self, configuration)
            self.builds[build_name] = build
            if build_name == default_build_name:
                self.default_build: bld.Build = build
                self.default_build_name = build_name

        self.self_hash = self._compute_self_hash()

    def commit(self):
        if self.clone is None:
            return None
        branch, commit = self.clone.branch()
        return commit

    def branch(self):
        if self.clone is None:
            return None
        branch, commit = self.clone.branch()
        return branch

    @property
    def recursive_hash(self):
        if self._recursive_hash is None:
            raise Exception("Accessed recursive_hash before calling resolve_dependencies")
        return self._recursive_hash

    def resolve_dependencies(self, configuration):
        if self._recursive_hash is not None:
            raise Exception("Called resolve_dependencies twice")

        for build in self.builds.values():
            build.resolve_dependencies(configuration)

        self._recursive_hash = self._compute_recursive_hash()

    def serialize(self):
        serialized_component = {
            "license": self.license,
            "binary_archives": self.binary_archives,
            "build_from_source": self.build_from_source,
            "skip_post_install": self.skip_post_install,
            "add_to_path": self.add_to_path,
            "repository": self.repository,
            "default_build": self.default_build_name,
            "builds": {b.name: b.serialize() for b in self.builds.values()},
        }

        return serialized_component

    def _self_hash_material(self) -> str:
        """Returns the string that is hashed to compute the self_hash"""
        to_hash = ""
        for build_name in sorted(self.builds.keys()):
            to_hash += self.builds[build_name].build_hash

        commit = self.commit()
        if commit:
            to_hash += commit

        return to_hash

    def _compute_self_hash(self):
        """Computes self_hash.
        This hash is defined by the configuration of all the builds of the component and the current source commit, if
        the component has a repository name
        """
        return hash(self._self_hash_material())

    def _transitive_dependencies(self) -> Set["Component"]:
        """Returns all the Components on which any build of this component depends on, directly or indirectly"""
        dependency_actions = set()
        for build in self.builds.values():
            collect_dependencies(build.install, dependency_actions)

        dependency_components = set()
        for action in dependency_actions:
            if isinstance(action, any_of.AnyOfAction):
                continue
            dependency_components.add(action.component)
        return dependency_components

    def _recursive_hash_material(self) -> str:
        """Returns the string that is hashed to compute recursive_hash"""
        dependency_components = self._transitive_dependencies()

        to_hash = ""
        for d in sorted(dependency_components, key=lambda c: c.name):
            to_hash += d.self_hash
        return to_hash

    def _compute_recursive_hash(self) -> str:
        return hash(self._recursive_hash_material())

    def __str__(self):
        return f"Component {self.name}"

    def __repr__(self):
        s = f"Component {self.name}"
        for build in self.builds.values():
            s += "  " + str(build)
        return s


def collect_dependencies(root_action, collected_actions):
    if root_action in collected_actions:
        return collected_actions

    collected_actions.add(root_action)
    for d in root_action.dependencies_for_hash:
        collect_dependencies(d, collected_actions)
