from pathlib import Path

from ..utils import git
from ..conftest import OrchestraShim


def test_upgrade_when_remote_config_changes(orchestra: OrchestraShim, capsys):
    """Checks that `orchestra upgrade` does upgrade components when the remote configuration changes"""
    orchestra.loglevel = "DEBUG"
    orchestra("install", "-b", "component_A")
    out, err = capsys.readouterr()
    assert "Initial component_A configuration" in out

    # Modify the upstream configuration
    with open(orchestra.upstream_orchestra_dotdir / "config" / "components.yml") as f:
        config = f.read()
        config = config.replace("Initial component_A configuration", "Modified component_A configuration")

    with open(orchestra.upstream_orchestra_dotdir / "config" / "components.yml", "w") as f:
        f.write(config)

    git.commit_all(orchestra.upstream_orchestra_dir, msg="Updated configuration")
    orchestra("update")

    orchestra("upgrade", "-b")
    out, err = capsys.readouterr()
    assert "Modified component_A configuration" in out


def test_upgrade_when_remote_repo_changes(orchestra: OrchestraShim):
    """Checks that `orchestra upgrade` does upgrade components when the remote repository changes"""
    # Register initial repository state
    content_filename = "somefile"
    remote_repository_path = orchestra.default_remote_base_url / "component_A"
    remote_repository_content_path = Path(remote_repository_path / content_filename)

    orchestra("install", "-b", "component_A")

    # Modify remote repository
    modified_content = "modified content"
    remote_repository_content_path.write_text(modified_content)
    git.commit_all(remote_repository_path)

    orchestra("update")
    orchestra("upgrade", "-b")

    path_to_content_in_root = orchestra.orchestra_root / content_filename
    assert path_to_content_in_root.read_text() == modified_content
