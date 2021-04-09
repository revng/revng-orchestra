from pathlib import Path

from ...orchestra_shim import OrchestraShim
from ...utils import git


def test_binary_archives_ls(orchestra: OrchestraShim, capsys):
    """Checks that the `binary-archives ls` subcommand works"""
    archive_name = "binarch"
    orchestra.add_binary_archive(archive_name)
    archive_local_path = orchestra.configuration.binary_archives_local_paths[archive_name]
    out, err = capsys.readouterr()

    orchestra("binary-archives", "ls")
    out, err = capsys.readouterr()
    assert archive_local_path not in out

    orchestra("binary-archives", "ls", "-a")
    out, err = capsys.readouterr()
    assert archive_local_path in out

    orchestra("update")
    orchestra("binary-archives", "ls")
    out, err = capsys.readouterr()
    assert archive_local_path in out


def test_binary_archives_clean(orchestra: OrchestraShim):
    """Checks that `binary-archives clean` works"""
    archive_name = "binarch"
    orchestra.add_binary_archive(archive_name)
    orchestra("update")
    orchestra("clone", "component_A")

    orchestra("install", "-b", "--create-binary-archives", "component_A")
    component = orchestra.configuration.components["component_A"]
    build = component.default_build

    binary_archive_path_1 = build.install.locate_binary_archive()
    assert Path(binary_archive_path_1).exists(), "The binary archive was not created?"

    local_binary_archive_repo = orchestra.configuration.binary_archives_local_paths[archive_name]
    git.commit_all(local_binary_archive_repo)

    source_dir = build.configure.source_dir
    somefile = Path(source_dir) / "somefile"
    somefile.write_text("some text just to change the file hash and commit it")
    git.commit_all(source_dir)

    orchestra("install", "-b", "--create-binary-archives", "component_A")
    # Note: it is fundamental to access again orchestra.configuration as it gives a new instance of Configuration that
    # accounts for the hash changes!
    component = orchestra.configuration.components["component_A"]
    build = component.default_build
    binary_archive_path_2 = build.install.locate_binary_archive()

    assert Path(binary_archive_path_2).exists(), "The binary archive was not created?"
    assert binary_archive_path_1 != binary_archive_path_2, "Binary archive path should have changed"

    orchestra("binary-archives", "clean")
    assert not Path(binary_archive_path_1).exists(), "This binary archive should have been deleted"
    assert Path(binary_archive_path_2).exists(), "This binary archive should have been kept"
