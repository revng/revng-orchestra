import json
import os
from textwrap import dedent
import pkg_resources

import jsonschema
import yaml

from ...actions.util import get_script_output, get_subprocess_output


def generate_yaml_configuration(orchestra_dotdir, use_cache=True):
    config_dir = os.path.join(orchestra_dotdir, "config")
    config_cache_file = os.path.join(orchestra_dotdir, "config_cache.json")
    yaml_config_cache_file = os.path.join(orchestra_dotdir, "config_cache.yml")
    config_hash = hash_config_dir(orchestra_dotdir)

    if use_cache and os.path.exists(config_cache_file):
        with open(config_cache_file) as f:
            cached_config = json.load(f)
            if config_hash == cached_config.get("config_hash"):
                return cached_config["config"]

    ytt = os.path.join(os.path.dirname(__file__), "..", "..", "support", "ytt")
    env = os.environ.copy()
    env["GOCG"] = "off"
    expanded_yaml = get_subprocess_output([ytt, "-f", config_dir], environment=env)
    parsed_config = yaml.safe_load(expanded_yaml)

    validate_configuration_schema(parsed_config)

    if use_cache:
        with open(config_cache_file, "w") as f:
            json.dump({"config_hash": config_hash, "config": parsed_config}, f)

        with open(yaml_config_cache_file, "w") as f:
            f.write(expanded_yaml)

    return parsed_config


def hash_config_dir(orchestra_dotdir):
    config_dir = os.path.join(orchestra_dotdir, "config")
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
        error_message = dedent("""
                Invalid configuration. Got the following error at path {path}:
                {message}
                """).format(path=error_path(e), message=e.message).strip()
        raise Exception(error_message) from e


# pip release of jsonschema does not yet include this commit
# which implements this function directly as a property of the error
# https://github.com/Julian/jsonschema/commit/1f37cb81c141df6a99bacc117b1549cc6702fa79
def error_path(err: jsonschema.ValidationError):
    path = '$'
    for elem in err.absolute_path:
        if isinstance(elem, int):
            path += '[' + str(elem) + ']'
        else:
            path += '.' + elem
    return path
