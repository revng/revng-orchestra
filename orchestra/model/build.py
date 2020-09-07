from ..actions import CloneAction
from ..actions import ConfigureAction
from ..actions import CreateBinaryArchivesActionAction
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

        self.clone: CloneAction = None
        self.configure: ConfigureAction = None
        self.install: InstallAction = None
        self.create_binary_archives: CreateBinaryArchivesActionAction = None

    @property
    def qualified_name(self):
        return f"{self.component.name}@{self.name}"

    def __str__(self):
        return f"Build {self.component.name}@{self.name}"
