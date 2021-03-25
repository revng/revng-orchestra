import os
import re
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


def expand_variables(string: str, additional_environment: "OrderedDict[str, str]" = None):
    """Expands environment variables in `string` using values taken from the system environment and the additional
    dictionary if supplied. Supported syntax:

    - `$VAR`, `${VAR}`: expaded to the value of VAR
    - `~` expanded to $HOME

    Variable names can only be alphanumerical and must start with a letter (matching [a-zA-Z_][a-zA-Z0-9_]*).
    If a variable is not set an exception will be raised.
    """
    full_environment = os.environ.copy()
    if additional_environment is not None:
        full_environment.update(additional_environment)

    expanded_string = string.replace("~", full_environment["HOME"])

    # Python regex do not support redefining the same named capture group twice, so we define name1 and name2.
    # Two groups are needed to match $VAR and ${VAR} forms
    # fmt: off
    var_regex = re.compile(
        r"\$(?P<name1>[a-zA-Z_][a-zA-Z0-9_])*"
        r"|\${(?P<name2>[a-zA-Z_][a-zA-Z0-9_]*)}"
    )
    # fmt: on
    match = var_regex.search(expanded_string)
    while match is not None:
        var_name = match.group("name1") or match.group("name2")
        var_value = full_environment.get(var_name)
        if var_value is None:
            raise ValueError(f"Variable {var_name} is not set while expanding environment for string `{string}`")
        expanded_string = var_regex.sub(var_value, expanded_string, count=1)
        match = var_regex.search(expanded_string)

    return expanded_string


def set_terminal_title(title):
    if sys.stdout.isatty():
        sys.stdout.write(f"\x1b]2;{title}\x07")
