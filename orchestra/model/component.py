import os
import json
import yaml
from functools import lru_cache
from pathlib import Path
from typing import Dict, Set, Union, Optional

from . import build as bld
from ._hash import hash
from ..actions import any_of
from ..actions import clone
from ..exceptions import UserException


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
        self._resolve_dependencies_called = False

        self.clone: Union[clone.CloneAction, None] = None
        if self.repository:
            self.clone = clone.CloneAction(self, self.repository, configuration)

        self.triggers = []
        if configuration.run_tests:
            self.triggers += serialized_component.get("test_triggers", [])

        # The default build is either specified, or the first in alphabetical order
        default_build_name = serialized_component.get("default_build")
        if default_build_name is None:
            default_build_name = sorted(serialized_component["builds"])[0]

        if default_build_name not in serialized_component["builds"]:
            raise UserException(f'Invalid default build "{default_build_name}" for component {name}')

        for build_name, build_yaml in serialized_component["builds"].items():
            build = bld.Build(build_name, build_yaml, self, configuration)
            self.builds[build_name] = build
            if build_name == default_build_name:
                self.default_build: bld.Build = build
                self.default_build_name = build_name

        self._orchestra_cache_dir = configuration.cache_dir
        self._configuration_hash = configuration.config_hash
        self._use_config_cache = configuration.use_config_cache

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
        assert self._recursive_hash is not None, "Accessed recursive_hash before calling compute_recursive_hash"
        return self._recursive_hash

    @lru_cache(maxsize=None, typed=False)
    def recursive_hash_material(self) -> str:
        """Returns the string that is hashed to compute recursive_hash"""
        assert self._resolve_dependencies_called, "Called recursive_hash_material before resolve_dependencies"
        hash_material = None

        if self._use_config_cache:
            hash_material = self._get_cached_hash_material()

        if hash_material is None:
            components_to_hash = list(self._transitive_dependencies())
            components_to_hash.sort(key=lambda c: c.name)
            hash_material = [c.serialize() for c in components_to_hash]

            hash_material = yamldump(hash_material)
            self._cache_hash_material(hash_material)

        return hash_material

    def _get_cached_hash_material(self) -> Optional[str]:
        assert self._resolve_dependencies_called, "Called _get_cached_hash_material before resolve_dependencies"
        if self._cache_filepath.exists():
            with open(self._cache_filepath) as f:
                cache_key_line = next(f)
                try:
                    cache_key = json.loads(cache_key_line)
                except json.JSONDecodeError:
                    return None

                version = cache_key.get("version")
                if version != 1:
                    return None

                config_hash = cache_key.get("config_hash")
                dep_commits = cache_key.get("dep_commits")

                if config_hash is None or dep_commits is None:
                    return None

                if config_hash != self._configuration_hash:
                    return None

                cached_dependencies_names = set(dep_commits.keys())
                actual_dependencies_names = {d.name for d in self._transitive_dependencies() if d.clone is not None}
                if cached_dependencies_names != actual_dependencies_names:
                    return None

                for dep in self._transitive_dependencies():
                    if dep_commits.get(dep.name) != dep.commit():
                        return None

                return f.read()
        return None

    def _cache_hash_material(self, hash_material: str):
        os.makedirs(self._cache_filepath.parent, exist_ok=True)

        cache_key = self._cache_key()

        with open(self._cache_filepath, "w") as f:
            f.write(json.dumps(cache_key))
            f.write("\n")
            f.write(hash_material)

    def _cache_key(self):
        return {
            "version": 1,
            "config_hash": self._configuration_hash,
            "dep_commits": {dep.name: dep.commit() for dep in self._transitive_dependencies() if dep.clone is not None},
        }

    @property
    def _cache_filepath(self) -> Path:
        return Path(self._orchestra_cache_dir) / "hash-material" / self._name_for_hash_material_cache

    @property
    def _name_for_hash_material_cache(self) -> str:
        return self.name.replace("/", "-")

    def resolve_dependencies(self, configuration):
        assert not self._resolve_dependencies_called, "Called resolve_dependencies twice"

        for build in self.builds.values():
            build.resolve_dependencies(configuration)

        self._resolve_dependencies_called = True

    def serialize(self):
        serialized_component = {
            "license": self.license,
            "skip_post_install": self.skip_post_install,
            "add_to_path": self.add_to_path,
            "repository": self.repository,
            "default_build": self.default_build_name,
            "builds": {b.name: b.serialize() for b in self.builds.values()},
            "commit": self.commit(),
        }

        return serialized_component

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

    def compute_recursive_hash(self):
        assert self._resolve_dependencies_called, "Called compute_recursive_hash before resolve_dependencies"

        if self._recursive_hash is None:
            hash_material = self.recursive_hash_material()
            self._recursive_hash = hash(hash_material)

    def __str__(self):
        return f"Component {self.name}"

    def __repr__(self):
        s = f"Component {self.name}"
        for build in self.builds.values():
            s += "  " + str(build)
        return s


def collect_dependencies(root_action, collected_actions):
    if root_action in collected_actions:
        return

    collected_actions.add(root_action)
    for d in root_action.dependencies_for_hash:
        collect_dependencies(d, collected_actions)


def yamldump(data):
    return yaml.dump(
        data,
        default_style="|",
        width=100000,
        sort_keys=True,
    )
