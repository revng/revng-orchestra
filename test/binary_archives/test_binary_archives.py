import subprocess
from textwrap import dedent

from orchestra.model import install_metadata
from ..conftest import OrchestraShim


def test_binary_archive_location(orchestra: OrchestraShim):
    """Checks that InstallAction returns the expected path for binary archives"""
    orchestra.add_binary_archive("origin")
    orchestra("update")
    component = orchestra.configuration.components["component_C"]
    build = component.builds["build0"]
    action = build.install

    commit = component.commit()
    if commit is None:
        commit = "none"

    expected_filename = f"{commit}_{component.recursive_hash}.tar.gz"
    expected_relative_path = f"{action.architecture}/{component.name}/{build.name}/{expected_filename}"
    assert action.binary_archive_filename == expected_filename
    assert action.binary_archive_relative_path == expected_relative_path


def test_binary_archives_creation(orchestra: OrchestraShim):
    """Checks binary archives are created correctly:
    - they are created at the expected location
    - they contain the expected files
    """
    orchestra.add_binary_archive("origin")
    orchestra("update")
    orchestra("install", "-b", "--create-binary-archives", "component_A")

    component = orchestra.configuration.components["component_A"]
    build = component.builds["build0"]

    expected_binary_archive_path = build.install.binary_archive_relative_path

    metadata = install_metadata.load_metadata(component.name, orchestra.configuration)
    assert metadata.binary_archive_path == expected_binary_archive_path

    build.install.binary_archive_exists()

    binary_archive_abs_path = build.install._binary_archive_path()
    files = subprocess.check_output(["tar", "tf", binary_archive_abs_path], encoding="utf-8").splitlines()
    files.sort()
    expected_files = sorted(
        [
            "bin/",
            "component_A_build0_file",
            "component_A_file",
            "include/",
            "lib",
            "lib64/",
            "lib64/include/",
            "lib64/pkgconfig/",
            "libexec/",
            "share/",
            "share/doc/",
            "share/man/",
            "share/orchestra/",
            "usr/",
            "usr/include/",
            "usr/lib/",
        ]
    )
    assert files == expected_files


def test_remote_heads_cache_poisoning_works(orchestra: OrchestraShim):
    """Checks that the mechanism for poisoning the remote HEADs cache works"""
    fake_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    fake_branch = "master"
    orchestra.configuration.remote_heads_cache.set_entry("component_C", fake_branch, fake_commit)
    component = orchestra.configuration.components["component_C"]
    assert component.commit() == fake_commit
    assert component.branch() == fake_branch
