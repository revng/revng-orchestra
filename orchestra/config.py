import subprocess
import yaml
import os


def gen_yaml(config_dir, use_cache=True):
    orchestra_dir = os.path.dirname(os.path.realpath(__file__ + "/.."))
    config_cache_dir = f"{orchestra_dir}/.orchestra/config_cache"

    if use_cache:
        hash_script = f"""find "{config_dir}" -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum"""
        config_hash = subprocess.check_output(hash_script, shell=True).decode("utf-8").strip().partition(" ")[0]
        # TODO: this method of obtaining the orchestra directory is a hack and is duplicated in environment.py
        config_cache_file = f"{config_cache_dir}/{config_hash}.yml"

        if os.path.exists(config_cache_file):
            with open(config_cache_file, "rb") as f:
                return f.read()

    expanded_yaml = subprocess.check_output(f"GOGC=off ytt -f {config_dir}", shell=True)

    if use_cache:
        os.makedirs(config_cache_dir, exist_ok=True)
        with open(config_cache_file, "wb") as f:
            f.write(expanded_yaml)

    return expanded_yaml


def gen_config(config_dir, use_cache=True):
    expanded_yaml = gen_yaml(config_dir, use_cache=use_cache)
    return yaml.safe_load(expanded_yaml)
