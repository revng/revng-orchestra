import subprocess
from collections import OrderedDict
from loguru import logger

from ..util import export_environment

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
        stdout = None
        stderr = None

    logger.debug(f"Executing script:\n{script}")
    result = subprocess.run(["/bin/bash", "-c", script_to_run], stdout=stdout, stderr=stderr)
    if check_returncode and result.returncode != 0:
        logger.error(f"Subprocess exited with exit code {result.returncode}")
        logger.error(f"Script executed: {export_environment(environment)}{script}")
        if quiet:
            stdout_content = try_decode(result.stdout)
            stderr_content = try_decode(result.stderr)
            logger.error(f"STDOUT: {stdout_content}")
            logger.error(f"STDERR: {stderr_content}")
        raise Exception("Script failed", result)

    return result


def try_decode(stream, encoding="utf-8"):
    try:
        return stream.decode(encoding)
    except Exception as e:
        return stream
