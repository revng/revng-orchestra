import subprocess
from collections import OrderedDict
from loguru import logger

from ..util import export_environment, OrchestraException

bash_prelude = """
set -o errexit
set -o nounset
set -o pipefail
"""

def run_script(script,
               quiet=False,
               environment: OrderedDict = None,
               strict_flags=True,
               check_returncode=True,
               ):
    """Helper for running shell scripts.
    :param script: the script to run
    :param quiet: if True the output of the command is not shown to the user,
    but instead captured and accessible from the `stdout` and `stderr` properties of the returned value.
    :param environment: will be exported at the beginning of the script
    :param strict_flags: if True, a prelude is prepended to the script to help catch errors
    :param check_returncode: if True an exception is raised unless the script returns 0
    :return: a subprocess.CompletedProcess instance
    """
    if strict_flags:
        script_to_run = bash_prelude
    else:
        script_to_run = ""

    if environment:
        script_to_run += export_environment(environment)

    script_to_run += script

    if quiet:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    else:
        logger.info(f"The following script is going to be executed:\n" + script.strip())
        logger.info(f"Script output:")
        stdout = None
        stderr = None

    result = subprocess.run(["/bin/bash", "-cx", script_to_run], stdout=stdout, stderr=stderr)
    if check_returncode and result.returncode != 0:
        raise OrchestraException(f"Script failed with return code {result.returncode}")

    return result


def try_decode(stream, encoding="utf-8"):
    try:
        return stream.decode(encoding)
    except Exception as e:
        return stream
