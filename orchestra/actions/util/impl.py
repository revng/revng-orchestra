import subprocess
from collections import OrderedDict

from loguru import logger

from ... import globals
from ...util import export_environment
from ...exceptions import UserScriptException, InternalScriptException, InternalSubprocessException

bash_prelude = """
set -o errexit
set -o nounset
set -o pipefail
"""


def _run_script(
    script,
    environment: [OrderedDict, dict] = None,
    strict_flags=True,
    cwd=None,
    loglevel="INFO",
    stdout=None,
    stderr=None,
):
    """Helper for running shell scripts.
    :param script: the script to run
    :param environment: will be exported at the beginning of the script
    :param strict_flags: if True, a prelude is prepended to the script to help catch errors
    :param cwd: if not None, the command is executed in the specified path
    :param loglevel: log debug informations at this level
    :param stdout: passed as the "stdout" parameter to subprocess.run
    :param stderr: passed as the "stderr" parameter to subprocess.run
    :return: a subprocess.CompletedProcess instance
    """
    if strict_flags:
        script_to_run = bash_prelude
    else:
        script_to_run = ""

    if environment:
        script_to_run += export_environment(environment)

    script_to_run += script

    logger.log(loglevel, f"The following script is going to be executed:\n" + script.strip())
    return subprocess.run(["/bin/bash", "-c", script_to_run], stdout=stdout, stderr=stderr, cwd=cwd)


def _run_internal_script(script, environment: OrderedDict = None, check_returncode=True, cwd=None):
    """Helper for running internal scripts.
    :param script: the script to run
    :param environment: optional additional environment variables
    :param check_returncode: if True, log an error and raise an InternalScriptException
                             when the script returns a nonzero exit code
    :param cwd: if not None, the command is executed in the specified path
    :returns: the exit code of the script
    """
    result = _run_script(
        script,
        environment=environment,
        loglevel="DEBUG",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
    )

    if check_returncode and result.returncode != 0:
        raise InternalScriptException(
            script=script,
            exitcode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    logger.debug(f"Script output was: \n{try_decode(result.stdout)}")

    return result.returncode


def _run_user_script(script, environment: OrderedDict = None, check_returncode=True, cwd=None):
    """Helper for running user scripts
    :param script: the script to run
    :param environment: optional additional environment variables
    :param check_returncode: if True, log an error and raise an UserScriptException
                             when the script returns a nonzero exit code
    :param cwd: if not None, the command is executed in the specified path
    """

    if globals.quiet:
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT
    else:
        stdout = None
        stderr = None

    result = _run_script(
        script,
        environment=environment,
        loglevel="INFO",
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
    )

    if check_returncode and result.returncode != 0:
        raise UserScriptException(
            script=script,
            exitcode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


def _get_script_output(
    script,
    environment: OrderedDict = None,
    check_returncode=True,
    decode_as="utf-8",
    cwd=None,
):
    """Helper for getting stdout of a script
    :param script: the script to run
    :param environment: optional additional environment variables
    :param check_returncode: if True, log an error and raise an InternalScriptException
                             when the script returns a nonzero exit code
    :param decode_as: decode the script output using this encoding
    :param cwd: if not None, the command is executed in the specified path
    :return: the stdout produced by the script or None if the script exits with a nonzero exit code
    :return: a tuple:
        - subprocess returncode
        - the decoded stdout
    """
    result = _run_script(
        script,
        environment=environment,
        loglevel="DEBUG",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
    )

    if check_returncode and result.returncode != 0:
        raise InternalScriptException(
            script=script,
            exitcode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return result.returncode, result.stdout.decode(decode_as)


def _run_subprocess(
    argv,
    environment: [OrderedDict, dict] = None,
    cwd=None,
    loglevel="INFO",
    stdout=None,
    stderr=None,
):
    """Helper for running a subprocess. Should not be used directly.
    :param argv: the argv passed to subprocess.run
    :param environment: environment variables
    :param cwd: if not None, the command is executed in the specified path
    :param loglevel: log debug informations at this level
    :param stdout: passed as the "stdout" parameter to subprocess.run
    :param stderr: passed as the "stderr" parameter to subprocess.run
    :return: a subprocess.CompletedProcess instance
    """

    message = f"The following program is going to be executed: {argv}"
    if cwd:
        message += f" in {cwd}"

    logger.log(loglevel, message)
    return subprocess.run(argv, stdout=stdout, stderr=stderr, cwd=cwd, env=environment)


def _run_internal_subprocess(
    argv,
    environment: [OrderedDict, dict] = None,
    cwd=None,
    check_returncode=True,
):
    """Helper for running an internal subprocess. Not to be used directly.
    :param argv: the argv passed to subprocess.run
    :param environment: environment variables
    :param cwd: if not None, the command is executed in the specified path
    :param check_returncode: if True, log an error and raise an InternalSubprocessException
                             when the script returns a nonzero exit code
    :returns: the exit code of the subprocess
    """

    result = _run_subprocess(
        argv,
        environment=environment,
        cwd=cwd,
        loglevel="DEBUG",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if check_returncode and result.returncode != 0:
        raise InternalSubprocessException(
            subprocess_args=argv,
            exitcode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    logger.debug(f"The subprocess output was: \n{try_decode(result.stdout)}")

    return result.returncode


def _get_subprocess_output(
    argv,
    environment=None,
    check_returncode=True,
    decode_as="utf-8",
    cwd=None,
):
    """
    Helper to run a subprocess and get its output
    :param argv: the argv passed to subprocess.run
    :param environment: environment variables
    :param check_returncode: if True, log an error and raise an InternalSubprocessException
                             when the subprocess returns a nonzero exit code
    :param decode_as: decode the output using this encoding
    :param cwd: if not None, the command is executed in the specified path
    :return: a tuple:
        - subprocess returncode
        - the decoded stdout
    """
    result = _run_subprocess(
        argv,
        environment=environment,
        loglevel="DEBUG",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
    )

    if check_returncode and result.returncode != 0:
        raise InternalSubprocessException(
            subprocess_args=argv,
            exitcode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return result.returncode, result.stdout.decode(decode_as)


def try_decode(stream, encoding="utf-8"):
    try:
        return stream.decode(encoding)
    except ValueError:
        return stream
