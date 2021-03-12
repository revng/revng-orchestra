import hashlib
from enum import Enum, auto
from functools import lru_cache
from typing import Dict, Union

from . import build
from ..actions import AnyOfAction
from ..actions import CloneAction


class Component:
    def __init__(
            self,
            name: str,
            serialized_component,
            configuration
    ):
        self.name = name
        self.builds: Dict[str, 'build.Build'] = {}
        self.skip_post_install = serialized_component.get("skip_post_install", False)
        self.license = serialized_component.get("license")
        self.from_source = serialized_component.get("build_from_source", False) or configuration.build_all_from_source
        self.binary_archives = serialized_component.get("binary_archives", None)

        self._default_build = None
        self._hash_state = ComponentHashState.NOT_READY

        self.clone: Union[CloneAction, None] = None
        repo = serialized_component.get("repository")
        if repo:
            self.clone = CloneAction(self, repo, configuration)

        # The default build is either specified, or the first in alphabetical order
        default_build_name = serialized_component.get("default_build")
        if default_build_name is None:
            default_build_name = sorted(serialized_component["builds"])[0]

        if default_build_name not in serialized_component["builds"]:
            raise Exception(f"Invalid default build \"{default_build_name}\" for component {name}")

        for build_name, build_yaml in serialized_component["builds"].items():
            bld = build.Build(build_name, build_yaml, self, configuration)
            self.builds[build_name] = bld
            if build_name == default_build_name:
                self.default_build = bld

        self._hash_state = ComponentHashState.SELF_HASH_READY

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

    def resolve_dependencies(self, configuration):
        if self._hash_state is not ComponentHashState.SELF_HASH_READY:
            raise Exception("Called resolve_dependencies at the wrong time")

        for build in self.builds.values():
            build.resolve_dependencies(configuration)

        self._hash_state = ComponentHashState.RECURSIVE_HASH_READY

    @property
    @lru_cache()
    def self_hash(self):
        if self._hash_state is ComponentHashState.NOT_READY:
            raise Exception(f"Accessed self_hash of non finalized component {self.name}")

        to_hash = ""
        for build_name in sorted(self.builds.keys()):
            to_hash += self.builds[build_name].build_hash

        commit = self.commit()
        if commit:
            to_hash += commit

        return hashlib.sha1(to_hash.encode("utf-8")).hexdigest()

    @property
    @lru_cache()
    def recursive_hash(self):
        if self._hash_state is not ComponentHashState.RECURSIVE_HASH_READY:
            raise Exception(f"Accessed recursive_hash of non finalized component {self.name}")

        dependency_actions = set()
        for build in self.builds.values():
            collect_dependencies(build.install, dependency_actions)

        dependency_components = set()
        for action in dependency_actions:
            if isinstance(action, AnyOfAction):
                continue
            dependency_components.add(action.component)

        dependency_components = list(dependency_components)
        dependency_components.sort(key=str)

        to_hash = ""
        for d in dependency_components:
            to_hash += d.self_hash

        return hashlib.sha1(to_hash.encode("utf-8")).hexdigest()

    def __str__(self):
        return f"Component {self.name}"

    def __repr__(self):
        s = f"Component {self.name}"
        for bld in self.builds.values():
            s += "  " + str(bld)
        return s


def collect_dependencies(root_action, collected_actions):
    if root_action in collected_actions:
        return collected_actions

    collected_actions.add(root_action)
    for d in root_action.dependencies_for_hash:
        collect_dependencies(d, collected_actions)


class ComponentHashState(Enum):
    NOT_READY = auto()
    SELF_HASH_READY = auto()
    RECURSIVE_HASH_READY = auto()
