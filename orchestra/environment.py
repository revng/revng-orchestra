from collections import OrderedDict
import os


def global_env(config):
    # TODO: this method of obtaining the orchestra directory is a hack
    orchestra = os.path.dirname(os.path.realpath(__file__ + "/.."))
    env = OrderedDict()
    # TODO: allow the user to configure the various paths
    # TODO: discuss if it is better to expand orchestra as it's done now or to use $ORCHESTRA
    path = f"{orchestra}/root/bin"
    path += f":{orchestra}/helpers"

    for _, component in config["components"].items():
        additional_path = component.get("additional_path")
        if additional_path:
            path += f":{additional_path}"

    path += "${PATH:+:${PATH}}"
    env["PATH"] = path
    env["ORCHESTRA"] = orchestra
    env["ORCHESTRA_ROOT"] = f"{orchestra}/root"
    env["SOURCE_ARCHIVES"] = f"{orchestra}/.orchestra/source_archives"
    env["PATCH_DIR"] = f"{orchestra}/patches"
    env["TMP_ROOT"] = f"{orchestra}/.orchestra/tmproot"
    env["JOBS"] = config["options"]["parallelism"]
    return env


def per_action_env(action):
    env = global_env(action.index.config)
    env["SOURCE_DIR"] = f"""{env["ORCHESTRA"]}/sources/{action.build.component.name}"""
    env["BUILD_DIR"] = f"""{env["ORCHESTRA"]}/build/{action.build.component.name}/{action.build.name}"""
    return env


def export_environment(variables: OrderedDict):
    env = ""
    for var, val in variables.items():
        env += f'export {var}="{val}"\n'
    return env
