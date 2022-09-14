from ..orchestra_shim import OrchestraShim
from ..fork_shim import ForkShim


def test_shell(orchestra: OrchestraShim, capsys):
    """Checks that `orchestra shell <cmd>` works"""
    with ForkShim() as shim:
        orchestra("shell", "echo", "Working")
        run = shim.get_last_execution()
        assert run.returncode == 0
        assert run.stdout == b"Working\n"

        orchestra("shell", "exit", "1")
        run = shim.get_last_execution()
        assert run.returncode == 1
