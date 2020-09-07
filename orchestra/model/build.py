from ..actions import CloneAction
from ..actions import ConfigureAction
from ..actions import InstallAction
from . import component


class Build:
    def __init__(
            self,
            name: str,
            comp: component.Component
    ):
        self.name = name
        self.component = comp
        self.self_hash = None
        self.recursive_hash = None

        self.clone: CloneAction = None
        self.configure: ConfigureAction = None
        self.install: InstallAction = None

    @property
    def qualified_name(self):
        return f"{self.component.name}@{self.name}"

    @property
    def safe_name(self):
        return self.qualified_name.replace("@", "_").replace("/", "_")

    @property
    def binary_archive_filename(self):
        return f'{self.safe_name}_{self.recursive_hash}.tar.gz'

    def __str__(self):
        return f"Build {self.component.name}@{self.name}"

    def __repr__(self):
        return f"Build {self.component.name}@{self.name}"
