from pathlib import Path

from .orchestra_shim import OrchestraShim


def test_clean(orchestra: OrchestraShim):
    """Checks that `orchestra clean` removes the build directory. Also tests the --pretend option."""
    orchestra("install", "-b", "component_A")

    build = orchestra.configuration.components["component_A"].default_build
    build_dir = Path(build.install.environment["BUILD_DIR"])

    orchestra("clean", "--pretend", "component_A")
    assert build_dir.exists()

    orchestra("clean", "component_A")
    assert not build_dir.exists()
