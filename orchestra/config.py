import subprocess
import yaml
import os


def hash_config_dir(config_dir):
    hash_script = f"""find "{config_dir}" -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum"""
    config_hash = subprocess.check_output(hash_script, shell=True).decode("utf-8").strip().partition(" ")[0]
    return config_hash


def gen_yaml(config_dir, use_cache=True):
    # TODO: this method of obtaining the orchestra directory is a hack and is duplicated in environment.py
    orchestra_dir = os.path.dirname(os.path.realpath(__file__ + "/.."))
    config_cache_dir = f"{orchestra_dir}/.orchestra"
    config_cache_file = f"{config_cache_dir}/config_cache"

    if use_cache:
        config_hash = hash_config_dir(config_dir)

        if os.path.exists(config_cache_file):
            with open(config_cache_file, "rb") as f:
                cached_hash = f.readline().decode("utf-8").strip()
                if config_hash == cached_hash:
                    return f.read()

    expanded_yaml = subprocess.check_output(f"GOGC=off ytt -f {config_dir}", shell=True)

    if use_cache:
        os.makedirs(config_cache_dir, exist_ok=True)

        with open(config_cache_file, "wb") as f:
            f.write(config_hash.encode("utf-8") + b"\n")
            f.write(expanded_yaml)

    return expanded_yaml


def gen_config(config_dir, use_cache=True):
    expanded_yaml = gen_yaml(config_dir, use_cache=use_cache)
    return yaml.safe_load(expanded_yaml)
