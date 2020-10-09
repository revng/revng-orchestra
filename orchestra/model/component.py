from typing import Dict

from . import build


class Component:
    def __init__(self,
                 name: str,
                 default_build_name: str,
                 skip_post_install=False,
                 ):
        self.name = name
        self.builds: Dict[str, 'build.Build'] = {}
        self.default_build_name = default_build_name
        self.skip_post_install = skip_post_install

    def add_build(self, bld: 'build.Build'):
        self.builds[bld.name] = bld

    @property
    def default_build(self):
        return self.builds[self.default_build_name]

    def __str__(self):
        return f"Component {self.name}"

    def __repr__(self):
        s = f"Component {self.name}"
        for bld in self.builds.values():
            s += "  " + str(bld)
        return s
