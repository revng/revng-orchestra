from test.orchestra_shim import OrchestraShim


def test_configure_simple_component(orchestra: OrchestraShim):
    """Checks that configuring a simple component with no dependencies does not fail"""
    orchestra("configure", "component_A")


def test_configure_component_with_dependencies(orchestra: OrchestraShim):
    """Checks that configuring a component with dependencies does not fail.
    Regression test against the following bug:
    Configuring a component with a dependency will trigger the install action of the dependency.
    The install action looks for command line arguments such as --no-merge and --keep-tmproot,
    which were not set by the configure command handler.
    """
    orchestra("configure", "-b", "component_B")


def test_configure_retriggers_on_failure(orchestra: OrchestraShim, capsys, monkeypatch):
    """Checks that configure is triggered again if it did not execute successfully"""
    monkeypatch.setenv("FAIL_CONFIGURE", "1")
    orchestra("install", "-b", "component_that_may_fail_configure", should_fail=True)

    out, err = capsys.readouterr()
    assert "Install" not in out

    monkeypatch.delenv("FAIL_CONFIGURE")
    orchestra("install", "-b", "component_that_may_fail_configure")

    out, err = capsys.readouterr()
    assert "Configure successful" in out
    assert "Installing" in out
