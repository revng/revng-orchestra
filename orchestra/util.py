import os.path

from .environment import global_env


def parse_component_name(component_spec):
    tmp = component_spec.split("@")
    component_name = tmp[0]
    build_name = tmp[1] if len(tmp) > 1 else None
    return component_name, build_name


def get_build_or_default(components, component_name, build_name):
    component = components.get(component_name)
    if not component:
        raise Exception(f"Component {component_name} not found!")

    if not build_name and "default_build" in component:
        build_name = component["default_build"]
    elif not build_name:
        build_name = list(component["builds"].keys())[0]

    build = component["builds"].get(build_name)
    if not build:
        raise Exception(f"Build {build_name} not found in {component_name}")

    return component, build_name, build


def install_component_path(component_name, config):
    return os.path.join(install_component_dir(config), component_name.replace("/", "_"))


def install_component_dir(config):
    env = global_env(config)
    return os.path.join(env["ORCHESTRA"], ".orchestra", "installed_components")


def get_installed(config, component_name):
    index_path = install_component_path(component_name, config)
    if not os.path.exists(index_path):
        return None, None

    with open(index_path) as f:
        installed_component, _, installed_build = f.readline().strip().partition("@")

    return installed_component, installed_build


def is_installed(config, wanted_component, wanted_build=None):
    installed_component, installed_build = get_installed(config, wanted_component)

    # Wanted component name must be equal
    # Wanted build name too, but only if if provided
    return wanted_component == installed_component and (not wanted_build or wanted_build == installed_build)
