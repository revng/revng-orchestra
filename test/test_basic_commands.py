from .orchestra_shim import OrchestraShim


def test_orchestra_environment(orchestra: OrchestraShim):
    """Checks that `orchestra environment` does not crash"""
    # TODO: test that orchestra environment returns an expected result.
    #  Problem: it includes absolute paths and relies on variable expansions
    orchestra("environment")


def test_shell(orchestra: OrchestraShim):
    """Checks that `orchestra shell <cmd>` works"""
    orchestra("shell", "echo", "Working")
    orchestra("shell", "exit", "1", should_fail=True)
