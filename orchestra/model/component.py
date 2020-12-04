from typing import Dict

from . import build

from ..actions.util import run_script

class Component:
    def __init__(self,
                 name: str,
                 default_build_name: str,
                 license: str,
                 from_source: bool,
                 binary_archives: str,
                 skip_post_install=False,
                 ):
        self.name = name
        self.builds: Dict[str, 'build.Build'] = {}
        self.default_build_name = default_build_name
        self.skip_post_install = skip_post_install
        self.license = license
        self.from_source = from_source
        self.clone: CloneAction = None
        self.binary_archives = binary_archives

    def add_build(self, bld: 'build.Build'):
        self.builds[bld.name] = bld

    @property
    def default_build(self):
        return self.builds[self.default_build_name]

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

    def __str__(self):
        return f"Component {self.name}"

    def __repr__(self):
        s = f"Component {self.name}"
        for bld in self.builds.values():
            s += "  " + str(bld)
        return s
