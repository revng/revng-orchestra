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
    # TODO: find a better way to export environment variables from components
    path += f":{orchestra}/root/x86_64-pc-linux-gnu/x86_64-pc-linux-gnu/gcc-bin/10.1.0"
    path += f":{orchestra}/root/x86_64-pc-linux-gnu/x86_64-pc-linux-gnu/binutils-bin/2.34"
    path += f":{orchestra}/root/x86_64-pc-linux-gnu/x86_64-pc-linux-gnu/binutils-bin/9.2"

    path += f":{orchestra}/root/x86_64-pc-linux-gnu/x86_64-gentoo-linux-musl/binutils-bin/2.25"
    path += f":{orchestra}/root/x86_64-pc-linux-gnu/x86_64-gentoo-linux-musl/binutils-bin/8.2.1"
    path += f":{orchestra}/root/x86_64-pc-linux-gnu/x86_64-gentoo-linux-musl/gcc-bin/4.9.3"

    path += f":{orchestra}/root/x86_64-pc-linux-gnu/s390x-ibm-linux-musl/binutils-bin/2.34"
    path += f":{orchestra}/root/x86_64-pc-linux-gnu/s390x-ibm-linux-musl/binutils-bin/8.2.1"
    path += f":{orchestra}/root/x86_64-pc-linux-gnu/s390x-ibm-linux-musl/gcc-bin/7.3.0"

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
