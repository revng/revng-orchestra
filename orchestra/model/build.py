from . import component
from .actions import CloneAction, ConfigureAction, InstallAction


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

    @property
    def qualified_name(self):
        return f"{self.component.name}@{self.name}"

    def __str__(self):
        return f"Build {self.name} of component {self.component.name}"
