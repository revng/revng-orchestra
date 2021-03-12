import json
import os
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
