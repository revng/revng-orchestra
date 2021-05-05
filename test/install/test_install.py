import os
import pytest
from textwrap import dedent

from ..orchestra_shim import OrchestraShim
from ..utils.json import load_json
from ..utils.filelist import compare_root_tree
from ..utils.metadata import compare_metadata


def assert_component_A_installed_properly(orchestra: OrchestraShim, metadata_overrides=None):
    component = orchestra.configuration.components["component_A"]

    # Test file list in root
    expected_file_list = {
        "./share/orchestra/component_A.idx",
        "./share/orchestra/component_A.json",
        "./some_file",
    }
    assert compare_root_tree(orchestra.orchestra_root, expected_file_list)

    # Test metadata
    expected_metadata = {
        "component_name": "component_A",
        "build_name": "default",
        "source": "build",
        "self_hash": component.self_hash,
        "recursive_hash": component.recursive_hash,
        "binary_archive_path": component.default_build.install.binary_archive_relative_path,
        "manually_installed": True,
    }
    if metadata_overrides:
        expected_metadata.update(metadata_overrides)
    metadata = load_json(orchestra.orchestra_root / "share/orchestra/component_A.json")
    assert compare_metadata(metadata, expected_metadata)

    # Test index (file list)
    expected_index = dedent(
        """
        some_file
        share/orchestra/component_A.idx
        share/orchestra/component_A.json
        """
    ).strip()
    with open(orchestra.orchestra_root / "share/orchestra/component_A.idx") as f:
        filelist = f.read().strip()
    assert expected_index == filelist


def test_install_from_source_with_no_binary_archives_configured(orchestra: OrchestraShim, capsys):
    """Checks that --fallback-build (-b) causes installation from source if no binary archives repositories are
    configured
    """
    orchestra.loglevel = "DEBUG"
    orchestra("install", "-b", "component_A")

    # Check the install script was run
    out, err = capsys.readouterr()
    assert "Executing install script" in out

    assert_component_A_installed_properly(orchestra)


def test_install_from_source_if_binary_archive_unavailable(orchestra: OrchestraShim, capsys):
    """Checks that --fallback-build (-b) causes installation from source if the binary archive for the component is not
    available
    """
    orchestra.add_binary_archive("origin")
    orchestra("update")

    orchestra.loglevel = "DEBUG"
    orchestra("install", "-b", "component_A")

    # Check the install script was run
    out, err = capsys.readouterr()
    assert "Executing install script" in out

    assert_component_A_installed_properly(orchestra)


def test_forced_install_from_source(orchestra: OrchestraShim, capsys):
    """Checks that --from-source (-B) forces installation from source, even if a binary archive is available"""
    orchestra.loglevel = "DEBUG"
    orchestra.add_binary_archive("origin")
    orchestra("update")
    orchestra("install", "-b", "--create-binary-archives", "component_A")
    out, err = capsys.readouterr()
    assert "Executing install script" in out

    orchestra.clean_root()
    orchestra("clean", "--include-sources", "component_A")

    orchestra("install", "-B", "component_A")
    out, err = capsys.readouterr()
    assert "Executing install script" in out

    assert_component_A_installed_properly(orchestra)


def test_install_from_binary_archives(orchestra: OrchestraShim, capsys):
    """Checks that installation from binary archives works"""
    orchestra.loglevel = "DEBUG"
    orchestra.add_binary_archive("origin")
    orchestra("update")
    orchestra("install", "-b", "--create-binary-archives", "component_A")
    out, err = capsys.readouterr()
    assert "Executing install script" in out

    orchestra.clean_root()
    orchestra("clean", "--include-sources", "component_A")

    orchestra("install", "component_A")
    out, err = capsys.readouterr()
    assert "Executing install script" not in out

    assert_component_A_installed_properly(orchestra, metadata_overrides={"source": "binary archives"})


def test_install_fails_if_no_binary_archives_configured(orchestra: OrchestraShim):
    """Checks that installation fails and no actions are executed if no binary archives are configured"""
    with pytest.raises(Exception):
        orchestra("install", "component_A")


def test_install_fails_if_binary_archives_unavailable(orchestra: OrchestraShim):
    """Checks that installation fails and no actions are executed if a binary archive is not available"""
    orchestra.add_binary_archive("origin")
    orchestra("update")

    with pytest.raises(Exception):
        orchestra("install", "component_A")


def test_install_conflicting_builds(orchestra: OrchestraShim):
    """Checks filesystem state when installing a build over a conflicting one.
    When installing a build of a component over another build of the same component
    the currently installed build is uninstalled."""
    orchestra("install", "-b", "component_B@build0")
    expected_file_list_1 = {
        "./share/orchestra/component_B.idx",
        "./share/orchestra/component_B.json",
        "./some_file",
    }
    assert compare_root_tree(orchestra.orchestra_root, expected_file_list_1)

    orchestra("install", "-b", "component_B@build1")
    expected_file_list_2 = {
        "./share/orchestra/component_B.idx",
        "./share/orchestra/component_B.json",
        "./some_other_file",
    }
    assert compare_root_tree(orchestra.orchestra_root, expected_file_list_2)


def test_test_option_runs_tests(orchestra: OrchestraShim):
    """Checks that the --test option sets the RUN_TESTS environment variable"""
    orchestra("install", "-B", "--test", "component_that_tests_test_option")


def test_no_merge(orchestra: OrchestraShim):
    """Checks that the --no-merge option works"""
    orchestra("install", "-b", "--no-merge", "component_A")
    assert not orchestra.orchestra_root.exists(), "orchestra root should not be created"


def test_keep_tmproot(orchestra: OrchestraShim):
    """Checks that the --keep-tmproot option works"""
    orchestra("install", "-b", "--keep-tmproot", "component_A")
    assert os.path.exists(orchestra.configuration.components["component_A"].default_build.install.tmp_root)
