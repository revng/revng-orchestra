from abc import ABC
from shlex import quote
from typing import List
from typing import Optional

from loguru import logger


class OrchestraException(Exception, ABC):
    """Base class for all exceptions raised by orchestra"""

    def __init__(self, message):
        super(OrchestraException, self).__init__(message)
        self.message = message

    def log_error(self):
        logger.error(self.message)
        if self.__cause__ is not None:
            logger.debug(f"The following exception was the direct cause of this exception:\n{self.__cause__}")


class UserException(OrchestraException):
    """Base class for all exceptions raised for any reason not attributable to orchestra code.
    For example, wrong configuration syntax, missing binary archives, a configure/install script failing, ...
    """

    def __init__(self, message):
        super(UserException, self).__init__(message)


class InternalException(OrchestraException):
    """Base class for all exceptions raised due to an orchestra programming error"""

    def __init__(self, message):
        super(InternalException, self).__init__(message)


class YTTException(UserException):
    """Raised when ytt invocation fails
    Note: it is important to use `raise YTTException() from InternalSubprocessError"""

    def __init__(self):
        super(YTTException, self).__init__("ytt invocation failed")

    def log_error(self):
        assert isinstance(self.__cause__, InternalSubprocessException)
        cause = self.__cause__
        message = f"ytt error ({quote_shell_args(cause.subprocess_args)})"

        if cause.stdout:
            message += f"\n{try_decode(cause.stdout)}"
        if cause.stderr:
            message += f"\n{try_decode(cause.stderr)}"

        logger.error(message)


class UserCommandException(UserException, ABC):
    """Base class for when a user-provided script or subprocess fails"""

    def __init__(
        self,
        message: str,
        exitcode: Optional[int] = None,
        stdout: Optional[bytes] = None,
        stderr: Optional[bytes] = None,
    ):
        super(UserCommandException, self).__init__(message)
        self.exitcode: Optional[int] = exitcode
        self.stdout: Optional[bytes] = stdout
        self.stderr: Optional[bytes] = stderr


class UserScriptException(UserCommandException):
    """Raised when a user-provided script fails"""

    def __init__(
        self,
        script: str,
        exitcode: Optional[int] = None,
        stdout: Optional[bytes] = None,
        stderr: Optional[bytes] = None,
    ):
        super(UserScriptException, self).__init__("Script failed", exitcode=exitcode, stdout=stdout, stderr=stderr)
        self.script: str = script

    def log_error(self):
        logger.error(str(self))

    def __str__(self):
        if self.exitcode is not None:
            s = f"Script failed with exit code {self.exitcode}"
        else:
            s = f"Script failed"

        if self.stdout:
            s += f"\nOutput stream:\n{try_decode(self.stdout)}\n"

        if self.stderr:
            s += f"\nError stream:\n{try_decode(self.stderr)}\n"

        return s


class InternalCommandException(InternalException, ABC):
    """Raised when an error occurs while executing an internal command that was not expected to fail"""

    def __init__(
        self,
        message: str,
        exitcode: Optional[int] = None,
        stdout: Optional[bytes] = None,
        stderr: Optional[bytes] = None,
    ):
        super(InternalCommandException, self).__init__(message)
        self.exitcode: Optional[int] = exitcode
        self.stdout: Optional[bytes] = stdout
        self.stderr: Optional[bytes] = stderr


class InternalSubprocessException(InternalCommandException):
    """Raised when an internal subprocess fails"""

    def __init__(
        self,
        subprocess_args: List[str],
        exitcode: Optional[int] = None,
        stdout: Optional[bytes] = None,
        stderr: Optional[bytes] = None,
    ):
        super(InternalSubprocessException, self).__init__(
            "Internal subprocess failed", exitcode=exitcode, stdout=stdout, stderr=stderr
        )
        self.subprocess_args: List[str] = subprocess_args

    def log_error(self):
        logger.error(str(self))

    def __str__(self):
        if self.exitcode is not None:
            s = f"Internal subprocess failed with exit code {self.exitcode}:\n"
        else:
            s = f"Internal subprocess failed:\n"

        s += f"{quote_shell_args(self.subprocess_args)}\n"

        if self.stdout:
            s += f"Output stream:\n{try_decode(self.stdout)}\n"

        if self.stderr:
            s += f"Error stream:\n{try_decode(self.stderr)}\n"

        return s


class InternalScriptException(InternalCommandException):
    """Raised when an internal script fails"""

    def __init__(
        self,
        script: str,
        exitcode: Optional[int] = None,
        stdout: Optional[bytes] = None,
        stderr: Optional[bytes] = None,
    ):
        super(InternalScriptException, self).__init__(
            "Internal script failed", exitcode=exitcode, stdout=stdout, stderr=stderr
        )
        self.script: str = script

    def log_error(self):
        logger.error(str(self))

    def __str__(self):
        if self.exitcode is not None:
            s = f"Internal script failed with exit code {self.exitcode}:\n"
        else:
            s = f"Internal script failed:\n"

        s += f"{self.script}\n"

        if self.stdout:
            s += f"Output stream:\n{try_decode(self.stdout)}\n"

        if self.stderr:
            s += f"Error stream:\n{try_decode(self.stderr)}\n"

        return s


def try_decode(stream, encoding="utf-8"):
    try:
        return stream.decode(encoding)
    except ValueError:
        return stream


def quote_shell_args(args_list: List[str]):
    return " ".join(quote(a) for a in args_list)
