from ..orchestra_shim import OrchestraShim


def test_shell(orchestra: OrchestraShim):
    """Checks that `orchestra shell <cmd>` works"""
    orchestra("shell", "echo", "Working")
    orchestra("shell", "exit", "1", should_fail=True)
