import subprocess
from textwrap import dedent

from .orchestra_shim import OrchestraShim


def test_uninstall(orchestra: OrchestraShim):
    """Checks that uninstall uninstalls
    all and only the files of the correct component"""
    orchestra("install", "-b", "component_A")
    orchestra("install", "-b", "component_B")
    orchestra("uninstall", "component_A")

    expected_file_list = dedent(
        """
    .
    ./bin/
    ./component_B_file
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
    ./usr/
    ./usr/include/
    ./usr/lib/
    """
    ).strip()
    file_list = tree(orchestra.orchestra_root)
    assert expected_file_list == file_list


def tree(dir):
    return subprocess.check_output(["tree", "-naifF", "--noreport"], cwd=dir).strip().decode("utf8")
