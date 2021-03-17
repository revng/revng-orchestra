import sys
from collections import OrderedDict


class OrchestraException(Exception):
    pass


def parse_component_name(component_spec):
    tmp = component_spec.split("@")
    component_name = tmp[0]
    build_name = tmp[1] if len(tmp) > 1 else None
    return component_name, build_name


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
