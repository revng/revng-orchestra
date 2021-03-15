import re
import subprocess

from .orchestra_shim import OrchestraShim


def test_clean(orchestra: OrchestraShim, capsys):
    """Checks that `orchestra clean` removes the build directory.
    Also tests the --pretend option."""
    orchestra("install", "-b", "component_A")
    capsys.readouterr()
    orchestra("environment", "component_A")
    out, err = capsys.readouterr()

    build_dir = re.search(r"export BUILD_DIR=\"(.*)\"", out).group(1)
    expected_build_dir = orchestra.builds_dir / "component_A" / "default"
    assert build_dir == str(expected_build_dir)
    assert expected_build_dir.exists()

    source_dir = re.search(r"export SOURCE_DIR=\"(.*)\"", out).group(1)
    expected_source_dir = orchestra.sources_dir / "component_A"
    assert source_dir == str(expected_source_dir)
    assert expected_source_dir.exists()

    orchestra("clean", "--pretend", "component_A")
    assert expected_build_dir.exists()
    assert expected_source_dir.exists()

    orchestra("clean", "component_A")
    assert not expected_build_dir.exists()
    assert expected_source_dir.exists()


def test_clean_include_sources(orchestra: OrchestraShim, capsys):
    """Checks that `orchestra clean --include-sources`
    removes both the build directory and the source directory.
    Also tests the --pretend option."""
    orchestra("install", "-b", "component_A")
    capsys.readouterr()
    orchestra("environment", "component_A")
    out, err = capsys.readouterr()

    build_dir = re.search(r"export BUILD_DIR=\"(.*)\"", out).group(1)
    expected_build_dir = orchestra.builds_dir / "component_A" / "default"
    assert build_dir == str(expected_build_dir)
    assert expected_build_dir.exists()

    source_dir = re.search(r"export SOURCE_DIR=\"(.*)\"", out).group(1)
    expected_source_dir = orchestra.sources_dir / "component_A"
    assert source_dir == str(expected_source_dir)
    assert expected_source_dir.exists()

    orchestra("clean", "--include-sources", "--pretend", "component_A")
    assert expected_build_dir.exists()
    assert expected_source_dir.exists()

    orchestra("clean", "--include-sources", "component_A")
    assert not expected_build_dir.exists()
    assert not expected_source_dir.exists()


def tree(dir):
    return subprocess.check_output(["tree", "-naifF", "--noreport"], cwd=dir).strip().decode("utf8")
