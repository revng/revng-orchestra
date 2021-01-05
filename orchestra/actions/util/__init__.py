from collections import OrderedDict

from .impl import _get_script_output
from .impl import _get_subprocess_output
from .impl import _run_internal_script
from .impl import _run_internal_subprocess
from .impl import _run_user_script


def run_internal_script(script, environment: OrderedDict = None):
    """Helper for running internal scripts.
    If the script returns a nonzero exit code an OrchestraException is raised.
    :param script: the script to run
    :param environment: optional additional environment variables
    :return: a subprocess.CompletedProcess instance
    """
    return _run_internal_script(script, environment=environment, check_returncode=True)


def try_run_internal_script(script, environment: OrderedDict = None):
    """Helper for running internal scripts.
    :param script: the script to run
    :param environment: optional additional environment variables
    :return: a subprocess.CompletedProcess instance
    """
    return _run_internal_script(script, environment=environment, check_returncode=False)


def run_user_script(script, environment: OrderedDict = None):
    """Helper for running user scripts.
    If the script returns a nonzero exit code an OrchestraException is raised.
    :param script: the script to run
    :param environment: optional additional environment variables
    :return: a subprocess.CompletedProcess instance
    """
    return _run_user_script(script, environment=environment, check_returncode=True)


def try_run_user_script(script, environment: OrderedDict = None):
    """Helper for running user scripts.
    :param script: the script to run
    :param environment: optional additional environment variables
    :return: a subprocess.CompletedProcess instance
    """
    return _run_user_script(script, environment=environment, check_returncode=False)


def get_script_output(script, environment: OrderedDict = None, decode_as="utf-8"):
    """Helper for getting stdout of a script.
    If the script returns a nonzero exit code an OrchestraException is raised.
    :param script: the script to run
    :param environment: optional additional environment variables
    :param decode_as: decode the script output using this encoding
    :return: the stdout produced by the script
    """
    return _get_script_output(script, environment=environment, check_returncode=True, decode_as=decode_as)


def try_get_script_output(script, environment: OrderedDict = None, decode_as="utf-8"):
    """Helper for getting stdout of a script. If the script returns nonzero an empty output will be returned.
    :param script: the script to run
    :param environment: optional additional environment variables
    :param decode_as: decode the script output using this encoding
    :return: the stdout produced by the script
    """
    return _get_script_output(script, environment=environment, check_returncode=False, decode_as=decode_as)


def run_internal_subprocess(
        argv,
        environment: [OrderedDict, dict] = None,
        cwd=None,
):
    """Helper for running an internal subprocess.
    If the subprocess returns a nonzero exit code an OrchestraException is raised.
    :param argv: the argv passed to subprocess.run
    :param environment: environment variables
    :param cwd: if not None, the command is executed in the specified path
    :return: a subprocess.CompletedProcess instance
    """
    return _run_internal_subprocess(argv, environment=environment, cwd=cwd, check_returncode=True)


def try_run_internal_subprocess(
        argv,
        environment: [OrderedDict, dict] = None,
        cwd=None,
):
    """Helper for running an internal subprocess.
    :param argv: the argv passed to subprocess.run
    :param environment: environment variables
    :param cwd: if not None, the command is executed in the specified path
    :return: a subprocess.CompletedProcess instance
    """
    return _run_internal_subprocess(argv, environment=environment, cwd=cwd, check_returncode=False)


def get_subprocess_output(
        argv,
        environment=None,
        decode_as="utf-8",
):
    """
    Helper to run a subprocess and get its output.
    If the subprocess returns a nonzero exit code an OrchestraException is raised.
    :param argv: the argv passed to subprocess.run
    :param environment: environment variables
    :param decode_as: decode the output using this encoding
    :return: the decoded stdout of the subprocess
    """
    return _get_subprocess_output(argv, environment=environment, decode_as=decode_as, check_returncode=True)


def try_get_subprocess_output(
        argv,
        environment=None,
        decode_as="utf-8",
):
    """
    Helper to run a subprocess and get its output.
    :param argv: the argv passed to subprocess.run
    :param environment: environment variables
    :param decode_as: decode the output using this encoding
    :return: the decoded stdout of the subprocess
    """
    return _get_subprocess_output(argv, environment=environment, decode_as=decode_as, check_returncode=False)
