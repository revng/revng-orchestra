import pytest
import subprocess
from textwrap import dedent

from ..orchestra_shim import OrchestraShim
from ..utils import load_json


def check_component_A_installed_properly(orchestra, metadata_overrides={}):
    # Test file list in root
    expected_file_list = dedent(
        """
    .
    ./bin/
    ./include/
    ./lib -> lib64/
    ./lib64/
    ./lib64/include/
    ./lib64/pkgconfig/
    ./libexec/
    ./share/
    ./share/doc/
    ./share/man/
    ./share/orchestra/
    ./share/orchestra/component_A.idx
    ./share/orchestra/component_A.json
    ./some_file
    ./usr/
    ./usr/include/
    ./usr/lib/
    """
    ).strip()
    file_list = tree(orchestra.orchestra_root)
    assert expected_file_list == file_list

    # Test metadata
    expected_metadata = {
        "component_name": "component_A",
        "build_name": "default",
        "source": "build",
        "self_hash": "46f755d2944e3d9e8d70a327416cc7ceacab4764",
        "recursive_hash": "82c4e547525d96aa4e60cc324ff18c3bb5ecda34",
        "binary_archive_path": "component_A/default/none_82c4e547525d96aa4e60cc324ff18c3bb5ecda34.tar.gz",
        "manually_installed": True,
    }
    expected_metadata.update(metadata_overrides)
    metadata = load_json(orchestra.orchestra_root / "share/orchestra/component_A.json")
    assert_same_metadata(metadata, expected_metadata)

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
    """Checks that --fallback-build (-b) causes installation from source if
    no binary archives repositories are configured"""
    orchestra("install", "-b", "component_A")

    # Check the install script was run
    out, err = capsys.readouterr()
    assert "Executing install script" in out

    check_component_A_installed_properly(orchestra)


def test_install_from_source_if_binary_archive_unavailable(orchestra: OrchestraShim, capsys):
    """Checks that --fallback-build (-b) causes installation from source if
    the binary archive for the component is not available"""
    orchestra.add_binary_archive("origin")
    orchestra("update")

    orchestra("install", "-b", "component_A")

    # Check the install script was run
    out, err = capsys.readouterr()
    assert "Executing install script" in out

    check_component_A_installed_properly(orchestra)


def test_forced_install_from_source(orchestra: OrchestraShim, capsys):
    """Checks that --from-source (-B) forces installation from source,
    even if a binary archive is available"""
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

    check_component_A_installed_properly(orchestra)


def test_install_from_binary_archives(orchestra: OrchestraShim, capsys):
    """Checks that installation from binary archives works"""
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

    check_component_A_installed_properly(orchestra, metadata_overrides={"source": "binary archives"})


def test_install_fails_if_no_binary_archives_configured(orchestra: OrchestraShim):
    """Checks that installation fails and no actions are executed if
    no binary archives are configured"""
    with pytest.raises(Exception):
        orchestra("install", "component_A")


def test_install_fails_if_binary_archives_unavailable(orchestra: OrchestraShim):
    """Checks that installation fails and no actions are executed if
    a binary archive is not available"""
    orchestra.add_binary_archive("origin")
    orchestra("update")

    with pytest.raises(Exception):
        orchestra("install", "component_A")


def test_install_conflicting_builds(orchestra: OrchestraShim):
    """Checks filesystem state when installing a build over a conflicting one.
    When installing a build of a component over another build of the same component
    the currently installed build is uninstalled."""
    orchestra("install", "-b", "component_B@build0")
    expected_file_list_1 = dedent(
        """
    .
    ./bin/
    ./include/
    ./lib -> lib64/
    ./lib64/
    ./lib64/include/
    ./lib64/pkgconfig/
    ./libexec/
    ./share/
    ./share/doc/
    ./share/man/
    ./share/orchestra/
    ./share/orchestra/component_B.idx
    ./share/orchestra/component_B.json
    ./some_file
    ./usr/
    ./usr/include/
    ./usr/lib/
    """
    ).strip()
    file_list_1 = tree(orchestra.orchestra_root)
    assert expected_file_list_1 == file_list_1

    orchestra("install", "-b", "component_B@build1")
    expected_file_list_2 = dedent(
        """
    .
    ./bin/
    ./include/
    ./lib -> lib64/
    ./lib64/
    ./lib64/include/
    ./lib64/pkgconfig/
    ./libexec/
    ./share/
    ./share/doc/
    ./share/man/
    ./share/orchestra/
    ./share/orchestra/component_B.idx
    ./share/orchestra/component_B.json
    ./some_other_file
    ./usr/
    ./usr/include/
    ./usr/lib/
    """
    ).strip()
    file_list_2 = tree(orchestra.orchestra_root)
    assert expected_file_list_2 == file_list_2


def test_test_option_runs_tests(orchestra: OrchestraShim):
    """Checks that the --test option sets the RUN_TESTS environment variable"""
    orchestra("install", "-B", "--test", "component_that_tests_test_option")


def tree(dir):
    return subprocess.check_output(["tree", "-naifF", "--noreport"], cwd=dir).strip().decode("utf8")


def assert_same_metadata(actual_value, expected_value):
    # Test JSON metadata
    ignore_keys = [
        "install_time",
    ]
    # Exclude those keys from the comparison, but ensure they are defined
    for k in ignore_keys:
        del actual_value[k]

    assert actual_value == expected_value
