from subprocess import run, PIPE, CompletedProcess
from typing import Optional
from unittest.mock import patch


class ForkShim:
    def __init__(self):
        self.last_execution: Optional[CompletedProcess] = None

    def __enter__(self):
        self.patch = patch("orchestra.actions.util.impl.os").__enter__()
        self.patch.fork = lambda: 1
        self.patch.execvpe = self.fake_execvpe
        return self

    def __exit__(self, *args):
        self.patch.__exit__(self, *args)

    def fake_execvpe(self, file, args, env):
        assert file == args[0]
        # when running orc shell in tests, the handler is called twice
        # first with the right arguments and then with no arguments at all
        last_line = args[-1].splitlines()[-1]
        if last_line.startswith("exec"):
            return
        self.last_execution = run(args, stdout=PIPE, stderr=PIPE)

    def get_last_execution(self) -> CompletedProcess:
        assert self.last_execution is not None
        return self.last_execution
