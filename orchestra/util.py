import json
import os.path
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


def get_installed_metadata(component_name, config):
    """
    Returns the metadata dictionary for an installed component.
    If the component is not installed, returns None.
    """
    metadata_path = config.installed_component_metadata_path(component_name)
    if not os.path.exists(metadata_path):
        return None

    with open(metadata_path) as f:
        return json.load(f)


def get_installed_build(component_name, config):
    """
    Returns the name of the installed build for the given component name.
    If the component is not installed, returns None.
    """
    metadata = get_installed_metadata(component_name, config)
    if not metadata:
        return None

    return metadata.get("build_name", None)


def get_installed_hash(component_name, config):
    """
    Returns the recursive hash of an installed component.
    If the component is not installed, returns None.
    """
    metadata = get_installed_metadata(component_name, config)
    if not metadata:
        return None

    return metadata.get("recursive_hash", None)


def is_installed(config, wanted_component, wanted_build=None, wanted_recursive_hash=None):
    metadata = get_installed_metadata(wanted_component, config)
    if metadata is None:
        return False
    installed_build = metadata.get("build_name")
    installed_recursive_hash = metadata.get("recursive_hash")

    return installed_build is not None \
           and (wanted_build is None or installed_build == wanted_build) \
           and (wanted_recursive_hash is None or installed_recursive_hash == wanted_recursive_hash)


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
