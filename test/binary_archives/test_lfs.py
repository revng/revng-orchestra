from ..orchestra_shim import OrchestraShim
import orchestra.gitutils.lfs as lfs


def test_lfs_proper_install_detection(orchestra: OrchestraShim, monkeypatch):
    """Ensures that orchestra can detect when git lfs is not properly installed (i.e. ~/.gitconfig does not contain
    the right filters).
    This is done by overriding $HOME to a path which does not contain a .gitconfig file.
    """
    monkeypatch.setenv("HOME", "/tmp")
    lfs._lfs_install_checked = False
    orchestra("install", "-b", "component_C", should_fail=True)
