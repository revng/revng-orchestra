import pytest

from .data_manager import TestDataManager
from .git_repos_manager import GitReposManager
from .orchestra_shim import OrchestraShim


@pytest.fixture(scope="function")
def test_data_mgr(request, tmpdir):
    return TestDataManager(request, tmpdir)


@pytest.fixture(scope="function")
def orchestra(request, test_data_mgr):
    """
    Fixture that helps instantiating a configuration and running orchestra.
    Returns an OrchestraShim instance.

    This fixture is configured through the `orchestra` marker. Example:

    @pytest.mark.orchestra(setup_default_upstream=False)
    def test_something(orchestra):
        pass

    The kwargs supplied to the marker are the same of the OrchestraShim object
    """
    orchestra_marker = request.node.get_closest_marker("orchestra")
    if orchestra_marker is not None:
        additional_kwargs = orchestra_marker.kwargs
    else:
        additional_kwargs = {}

    return OrchestraShim(test_data_mgr, **additional_kwargs)


@pytest.fixture(scope="function")
def git_repos_manager(test_data_mgr):
    """
    Fixture that helps managing git repositories.
    Returns a GitReposManager instance.
    """
    return GitReposManager(test_data_mgr)


def pytest_configure(config):
    config.addinivalue_line("markers", "orchestra(setup_default_upstream=True): Orchestra fixture configuration marker")
