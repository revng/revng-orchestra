import subprocess
from textwrap import dedent

from ..conftest import OrchestraShim
from ..utils import load_json


def test_binary_archives_creation(orchestra: OrchestraShim):
    """Checks binary archives are created correctly:
    - they have the expected name
    - they contain the expected data
    """
    orchestra.add_binary_archive("origin")
    orchestra("update")
    orchestra("install", "-b", "--create-binary-archives", "component_A")

    expected_binary_archive_path = "component_A/default/none_cb020607ef8bbca7df62adafe54bec6b34adc39c.tar.gz"
    metadata = load_json(orchestra.orchestra_root / "share/orchestra/component_A.json")
    assert metadata["binary_archive_path"] == expected_binary_archive_path

    binary_archive_full_path = orchestra.binary_archives_dir / "origin/linux-x86-64/" / expected_binary_archive_path

    expected_files = (
        dedent(
            """
    bin/
    include/
    lib
    lib64/
    lib64/include/
    lib64/pkgconfig/
    libexec/
    share/
    share/doc/
    share/man/
    share/orchestra/
    some_file
    usr/
    usr/include/
    usr/lib/
    """
        )
        .strip()
        .splitlines()
    )
    files = subprocess.check_output(["tar", "tf", binary_archive_full_path], encoding="utf-8").splitlines()
    files.sort()
    assert files == expected_files


def test_remote_heads_cache_poisoning_works(orchestra: OrchestraShim):
    """Checks that the mechanism for poisoning the remote HEADs cache works"""
    fake_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    fake_branch = "master"
    orchestra.configuration.remote_heads_cache._set_entry("component_C", fake_branch, fake_commit)
    component = orchestra.configuration.components["component_C"]
    assert component.commit() == fake_commit
    assert component.branch() == fake_branch


def test_component_hashes(orchestra: OrchestraShim):
    """Checks that the component hashes are as expected"""
    # Test repositories are initialized each time, so, their commit IDs are not fixed.
    # Getting reproducible commit hashes is difficult and brittle,
    # and committing entire repositories is also not what we want.
    # So we lie to orchestra and fix the commit hash of component_C in the cache.
    fake_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    fake_branch = "master"
    orchestra.configuration.remote_heads_cache._set_entry("component_C", fake_branch, fake_commit)

    component = orchestra.configuration.components["component_C"]

    assert component.self_hash == "75ad645b83f6fa5a1e00431da57c8f4161414456"
    assert component.recursive_hash == "7ae44d32e074de7f4c987907c32a5250a59536f8"


def test_build_hashes(orchestra: OrchestraShim):
    """Checks that the build hashes are as expected"""
    # Test repositories are initialized each time, so, their commit IDs are not fixed.
    # Getting reproducible commit hashes is difficult and brittle,
    # and committing entire repositories is also not what we want.
    # So we lie to orchestra and fix the commit hash of component_C in the cache.
    fake_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    orchestra.configuration.remote_heads_cache._set_entry("component_C", "master", fake_commit)

    component = orchestra.configuration.components["component_C"]

    build = component.default_build
    assert build.build_hash == "f3f9f82a8e6b5e9cfa26546469350c475f103499"
