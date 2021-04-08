import re
import subprocess

from ..orchestra_shim import OrchestraShim


def test_postinstall_drop_absolute_pkgconfig_paths(orchestra: OrchestraShim):
    """Checks that the postinstall pass that drops absolute paths from pkgconfig files works"""
    orchestra("install", "-b", "component_that_tests_postinstall")

    pkgconfig_file = orchestra.orchestra_root / "lib/pkgconfig/test.pc"
    assert str(orchestra.orchestra_root) not in pkgconfig_file.read_text()


def test_postinstall_purge_libtool_files(orchestra: OrchestraShim):
    """Checks that the postinstall pass that drops libtool files works"""
    orchestra("install", "-b", "component_that_tests_postinstall")

    libtool_file = orchestra.orchestra_root / "usr/lib/test.la"
    assert not libtool_file.exists()


def test_postinstall_hard_to_symbolic(orchestra: OrchestraShim):
    """Checks that the postinstall pass that converts hardlinks to symbolic links works"""
    orchestra("install", "-b", "component_that_tests_postinstall")

    file1 = orchestra.orchestra_root / "file1"
    file2 = orchestra.orchestra_root / "file2"
    # before the postinstall file1 and file2 point to the same inode (hardlinks)
    # orchestra can choose to turn either one into a symlink pointing to the other
    if file2.is_symlink():
        link = file2
        dest = file1
    elif file1.is_symlink():
        link = file1
        dest = file2
    else:
        raise Exception("Either file1 or file2 must be a symlink")

    assert link.resolve() == dest


def test_postinstall_fix_rpath(orchestra: OrchestraShim, test_data_mgr, monkeypatch):
    """Checks that the postinstall pass that fixes the RPATH works"""
    project_sources_path = str(test_data_mgr.copy("sources"))
    monkeypatch.setenv("PROJECT_SOURCES", project_sources_path)

    orchestra("install", "-b", "component_that_tests_postinstall_rpath")

    binary_path = str(orchestra.orchestra_root / "bin" / "test")
    dynamic_section_entries = subprocess.check_output(["readelf", "-d", binary_path])
    regex = re.compile(rb"Library runpath: \[(.*)\]")
    match = regex.search(dynamic_section_entries)
    assert match is not None, "expected RUNPATH to be set"
    assert str(orchestra.orchestra_root).encode("utf-8") not in match.group(1)
    assert b"$ORIGIN" in match.group(1)


def test_postinstall_replace_ndebug(orchestra: OrchestraShim):
    """Checks that the postinstall pass that replaces NDEBUG preprocessor checks works"""
    orchestra("install", "-b", "component_that_tests_postinstall")

    header_file = orchestra.orchestra_root / "include" / "test.h"
    assert "NDEBUG" not in header_file.read_text()


def test_skip_post_install(orchestra: OrchestraShim):
    """Checks that the skip_post_install configuration option works"""
    orchestra("install", "-b", "component_that_skips_post_install")
    file1 = orchestra.orchestra_root / "file1"
    file2 = orchestra.orchestra_root / "file2"
    assert not file1.is_symlink(), "postinstall run and transformed a hardlink into a synlink"
    assert not file2.is_symlink(), "postinstall run and transformed a hardlink into a synlink"
