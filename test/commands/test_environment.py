from ..orchestra_shim import OrchestraShim


def test_orchestra_environment(orchestra: OrchestraShim):
    """Checks that `orchestra environment` does not crash"""
    # TODO: test that orchestra environment returns an expected result.
    #       Problem: it includes absolute paths and relies on variable expansions
    orchestra("environment")
