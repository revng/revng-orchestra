import json
import os.path
import re
from collections import OrderedDict
from typing import Union


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


def get_installed_build(component_name, config):
    """
    Returns the name of the installed build for the given component name.
    If the component is not installed, returns None.
    """
    metadata_path = config.installed_component_metadata_path(component_name)
    if not os.path.exists(metadata_path):
        return None

    with open(metadata_path) as f:
        metadata = json.load(f)

    return metadata.get("build_name", None)


def is_installed(config, wanted_component, wanted_build=None):
    installed_build = get_installed_build(wanted_component, config)

    return installed_build is not None and (wanted_build is None or installed_build == wanted_build)


def export_environment(variables: OrderedDict):
    env = ""
    for var, val in variables.items():
        env += f'export {var}="{val}"\n'
    return env
