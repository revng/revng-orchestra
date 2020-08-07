from itertools import repeat
from typing import Dict

from fuzzywuzzy import fuzz

from . import build as bld
from . import component as comp
from .actions import CloneAction, ConfigureAction, InstallAction, UninstallAction
from ..util import parse_component_name


class ComponentIndex:
    def __init__(self, configuration):
        self.config = configuration
        self.components: Dict[str, comp.Component] = {}
        self._parse_components()

    def get_build(self, comp_spec):
        component_name, build_name = parse_component_name(comp_spec)
        component = self.components.get(component_name)
        if not component:
            suggested_component_name = self.get_suggested_component_name(component_name)
            raise Exception(f"Component {component_name} not found! Did you mean {suggested_component_name}?")
        if build_name:
            build = component.builds[build_name]
        else:
            build = component.default_build
        return build

    def _parse_components(self):
        # First pass: create the component, its builds and actions with "internal" dependencies
        for component_name, component_yaml in self.config["components"].items():
            default_build = component_yaml.get("default_build")
            if not default_build:
                default_build = list(component_yaml["builds"])[0]

            component = comp.Component(component_name, default_build)
            self.components[component_name] = component

            for build_name, build_yaml in component_yaml["builds"].items():
                build = bld.Build(build_name, component)
                component.add_build(build)

                repo = component_yaml.get("repository")
                if repo:
                    clone_action = CloneAction(build, repo, self)
                    build.clone = clone_action

                configure_script = build_yaml["configure"]
                configure_action = ConfigureAction(build, configure_script, self)
                if build.clone:
                    configure_action.dependencies.add(build.clone)
                build.configure = configure_action

                install_script = build_yaml["install"]
                install_action = InstallAction(build, install_script, self)
                install_action.dependencies.add(build.configure)
                build.install = install_action

                build.uninstall = UninstallAction(build, self)

        # Second pass: resolve "external" dependencies
        for component_name, component_yaml in self.config["components"].items():
            component = self.components[component_name]

            for build_name, build_yaml in component_yaml["builds"].items():
                build = component.builds[build_name]

                dependencies = build_yaml.get("dependencies", [])
                build_dependencies = build_yaml.get("build_dependencies", [])
                # List of (dependency_name: str, build_only: bool)
                all_dependencies = []
                all_dependencies += list(zip(dependencies, repeat(False)))
                all_dependencies += list(zip(build_dependencies, repeat(True)))

                for dep, build_only in all_dependencies:
                    dep_comp_name, dep_build_name = parse_component_name(dep)
                    dep_comp = self.components[dep_comp_name]
                    if dep_build_name:
                        dep_build = dep_comp.builds[dep_build_name]
                    else:
                        dep_build = dep_comp.default_build

                    dep_action = dep_build.install

                    build.configure.dependencies.add(dep_action)

    def get_suggested_component_name(self, user_component_name):
        best_ratio = 0
        best_match = None
        for component_name in self.components:
            ratio = fuzz.ratio(user_component_name, component_name)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = component_name
        return best_match
