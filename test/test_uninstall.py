from .orchestra_shim import OrchestraShim
from .utils.filelist import compare_root_tree


def test_uninstall(orchestra: OrchestraShim):
    """Checks that uninstall uninstalls all and only the files of the correct component"""
    orchestra("install", "-b", "component_A")
    orchestra("install", "-b", "component_B")
    orchestra("uninstall", "component_A")

    expected_file_list = {
        "./component_B_file",
        "./component_B_build0_file",
        "./share/orchestra/component_B.idx",
        "./share/orchestra/component_B.json",
    }
    assert compare_root_tree(orchestra.orchestra_root, expected_file_list)
