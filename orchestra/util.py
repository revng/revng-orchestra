import re
import sys
from collections import OrderedDict
from typing import Union


class OrchestraException(Exception):
    pass


def parse_component_name(component_spec):
    tmp = component_spec.split("@")
    component_name = tmp[0]
    build_name = tmp[1] if len(tmp) > 1 else None
    return component_name, build_name


def parse_dependency(dependency) -> (str, Union[str, None], bool):
    """
    Dependencies can be specified in the following formats:
    - Simple:
        `component`
        Depend on the installation of the default build of `component`.
    - Exact:
        `component@build`
        Depend on the installation of a specific build of `component`
    - Simple with preferred build:
        `component~build`
        to depend on the installation of any build of `component`.
        If the component is not installed, the specified build is picked.

    :returns component_name, build_name, exact_build_required
                component_name: name of the requested component
                build_name: name of the requested build or None
                exact_build_required: True if build_name represents an exact requirement
    """
    dependency_re = re.compile(r"(?P<component>[\w\-_/]+)((?P<type>[@~])(?P<build>[\w\-_/]+))?")
    match = dependency_re.fullmatch(dependency)
    if not match:
        raise Exception(f"Invalid dependency specified: {dependency}")

    component = match.group("component")
    exact_build_required = False if match.group("type") == "~" else True
    build = match.group("build")

    return component, build, exact_build_required


def export_environment(variables: OrderedDict):
    env = ""
    for var, val in variables.items():
        if var.startswith("-"):
            var_name = var[1:]
            if val is not None and val != "":
                raise Exception(f"Requested environment variable {var_name} to be unset but its value is not empty")
            env += f'unset -v {var_name}\n'
        else:
            env += f'export {var}="{val}"\n'

    return env


def set_terminal_title(title):
    if sys.stdout.isatty():
        sys.stdout.write(f"\x1b]2;{title}\x07")
