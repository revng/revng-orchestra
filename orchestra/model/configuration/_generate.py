import json
import os
from pathlib import Path
from textwrap import dedent
from typing import Optional

import jsonschema
import pkg_resources
import yaml

from ...actions.util import get_script_output, get_subprocess_output
from ...exceptions import InternalSubprocessException, YTTException, UserException


def run_ytt(config_dir):
    ytt = os.path.join(os.path.dirname(__file__), "..", "..", "support", "ytt")
    env = os.environ.copy()
    env["GOCG"] = "off"
    try:
        expanded_yaml = get_subprocess_output(
            [ytt, "--dangerous-allow-all-symlink-destinations", "-f", config_dir],
            environment=env,
        )
        return expanded_yaml
    except InternalSubprocessException as e:
        raise YTTException from e


def generate_yaml_configuration(
    config_dir,
    cache_dir: Optional[Path] = None,
):
    config_hash = hash_config_dir(config_dir)

    if cache_dir is not None:
        os.makedirs(cache_dir, exist_ok=True)
        config_cache_file = cache_dir / "config_cache.json"
        yaml_config_cache_file = cache_dir / "config_cache.yml"
        if config_cache_file.exists():
            with open(config_cache_file) as f:
                cached_config = json.load(f)
                if config_hash == cached_config.get("config_hash"):
                    return cached_config["config"], config_hash

    expanded_yaml = run_ytt(config_dir)
    parsed_config = yaml.safe_load(expanded_yaml)

    if cache_dir is not None:
        with open(config_cache_file, "w") as f:
            json.dump({"config_hash": config_hash, "config": parsed_config}, f)

        with open(yaml_config_cache_file, "w") as f:
            f.write(expanded_yaml)

    return parsed_config, config_hash


def hash_config_dir(config_dir):
    hash_script = f"""find "{config_dir}" -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum"""
    config_hash = get_script_output(hash_script).strip().partition(" ")[0]
    return config_hash


def validate_configuration_schema(parsed_config):
    config_schema = pkg_resources.resource_stream("orchestra.support", "config.schema.yml")
    parsed_config_schema = yaml.safe_load(config_schema)

    try:
        jsonschema.validate(parsed_config, parsed_config_schema)
    except jsonschema.ValidationError as e:
        # Do not use f-strings, as they will break dedent if `message` contains newlines
        error_message = (
            dedent(
                """
                Invalid configuration. Got the following error at path {path}:
                {message}
                """
            )
            .format(path=error_path(e), message=e.message)
            .strip()
        )
        raise UserException(error_message)


# pip release of jsonschema does not yet include this commit
# which implements this function directly as a property of the error
# https://github.com/Julian/jsonschema/commit/1f37cb81c141df6a99bacc117b1549cc6702fa79
def error_path(err: jsonschema.ValidationError):
    path = "$"
    for elem in err.absolute_path:
        if isinstance(elem, int):
            path += "[" + str(elem) + "]"
        else:
            path += "." + elem
    return path
