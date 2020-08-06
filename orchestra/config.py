import subprocess
import yaml


def gen_yaml(config_dir):
    expanded_yaml = subprocess.check_output(f"ytt -f {config_dir}", shell=True)
    return expanded_yaml


def gen_config(config_dir):
    expanded_yaml = gen_yaml(config_dir)
    return yaml.safe_load(expanded_yaml)
