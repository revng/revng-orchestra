from ..orchestra_shim import OrchestraShim


def test_autotools_project(orchestra: OrchestraShim, test_data_mgr, monkeypatch):
    """Checks that a basic autotools-based project works"""
    project_sources_path = str(test_data_mgr.copy("sample_autotools_project"))
    monkeypatch.setenv("PROJECT_SOURCES", project_sources_path)

    orchestra("install", "-b", "sample_autotools_project")

    assert (orchestra.orchestra_root / "bin" / "test").exists()


def test_cmake_project(orchestra: OrchestraShim, test_data_mgr, monkeypatch):
    """Checks that a basic cmake-based project works"""
    project_sources_path = str(test_data_mgr.copy("sample_cmake_project"))
    monkeypatch.setenv("PROJECT_SOURCES", project_sources_path)

    orchestra("install", "-b", "--keep-tmproot", "sample_cmake_project")

    assert (orchestra.orchestra_root / "bin" / "test").exists()
