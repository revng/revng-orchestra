import logging
import subprocess
from collections import OrderedDict

from ...environment import export_environment

bash_prelude = """
set -o errexit
set -o nounset
set -o pipefail
"""


def run_script(script,
               show_output=False,
               environment: OrderedDict = None,
               strict_flags=True,
               check_returncode=True,
               ):
    if strict_flags:
        script_to_run = bash_prelude
    else:
        script_to_run = ""

    if environment:
        script_to_run += export_environment(environment)

    script_to_run += script

    if show_output:
        stdout = None
        stderr = None
    else:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE

    logging.debug(f"Executing: {script}")
    result = subprocess.run(script_to_run, shell=True, stdout=stdout, stderr=stderr)
    if check_returncode and result.returncode != 0:
        logging.error(f"Subprocess exited with exit code {result.returncode}")
        logging.error(f"Script executed: {script_to_run}")
        if not show_output:
            logging.error(f"STDOUT: {result.stdout}")
            logging.error(f"STDERR: {result.stderr}")
        raise Exception("Script failed", result)

    return result
