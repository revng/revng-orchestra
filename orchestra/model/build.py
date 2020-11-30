import hashlib
import os.path

from ..actions import CloneAction
from ..actions import ConfigureAction
from ..actions import InstallAction
from . import component
from ..actions.util import run_script


class Build:
    def __init__(
            self,
            name: str,
            comp: component.Component,
            serialized_build: str,
            ndebug=True,
            test=False,
    ):
        self.name = name
        self.component = comp
        self.serialized_build = serialized_build

        self.configure: ConfigureAction = None
        self.install: InstallAction = None

        self.ndebug = ndebug
        self.test = test

    @property
    def qualified_name(self):
        return f"{self.component.name}@{self.name}"

    @property
    def self_hash(self):
        serialized_build = self.serialized_build
        if self.component.clone:
            branch, commit = self.component.clone.get_remote_head()
            if commit:
                serialized_build = commit.encode("utf-8") + serialized_build
        return hashlib.sha1(serialized_build).hexdigest()

    @property
    def recursive_hash(self):
        # The recursive hash of a build depends on all its configure and install dependencies
        all_builds = {d.build for d in self.configure.external_dependencies}
        # TODO: are install dependencies required to be part of the information to hash?
        #  In theory they should not influence the artifacts
        all_builds.update({d.build for d in self.install.external_dependencies})
        # Filter out builds from the same component
        all_builds = [b for b in all_builds if b.component != self.component]

        # sorted_dependencies = [(b.qualified_name, b) for b in all_builds]
        # sorted_dependencies.sort()
        all_builds.sort(key=lambda b: b.qualified_name)

        to_hash = self.self_hash
        for b in all_builds:
            to_hash += b.recursive_hash

        return hashlib.sha1(to_hash.encode("utf-8")).hexdigest()

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
        return f'{component_commit}_{self.recursive_hash}.tar.gz'

    def __str__(self):
        return f"Build {self.component.name}@{self.name}"

    def __repr__(self):
        return f"Build {self.component.name}@{self.name}"
