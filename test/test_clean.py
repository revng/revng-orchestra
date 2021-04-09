from pathlib import Path

from .orchestra_shim import OrchestraShim


def test_clean(orchestra: OrchestraShim):
    """Checks that `orchestra clean` removes the build directory. Also tests the --pretend option."""
    orchestra("install", "-b", "component_A")

    build = orchestra.configuration.components["component_A"].default_build
    build_dir = Path(build.install.environment["BUILD_DIR"])
    source_dir = Path(build.install.environment["SOURCE_DIR"])

    orchestra("clean", "--pretend", "component_A")
    assert build_dir.exists()
    assert source_dir.exists()

    orchestra("clean", "component_A")
    assert not build_dir.exists()
    assert source_dir.exists()


def test_clean_include_sources(orchestra: OrchestraShim):
    """Checks that `orchestra clean --include-sources` removes both the build directory and the source directory.
    Also tests the --pretend option.
    """
    orchestra("install", "-b", "component_A")

    build = orchestra.configuration.components["component_A"].default_build
    build_dir = Path(build.install.environment["BUILD_DIR"])
    source_dir = Path(build.install.environment["SOURCE_DIR"])

    orchestra("clean", "--include-sources", "--pretend", "component_A")
    assert build_dir.exists()
    assert source_dir.exists()

    orchestra("clean", "--include-sources", "component_A")
    assert not build_dir.exists()
    assert not source_dir.exists()
