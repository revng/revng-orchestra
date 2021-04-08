from pathlib import Path

from ..utils import git
from ..conftest import OrchestraShim


def test_update_orchestra_configuration(orchestra: OrchestraShim, capsys):
    """Checks that `orchestra update` updates orchestra configuration"""
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

    orchestra("install", "-b", "component_A")
    out, err = capsys.readouterr()
    assert "Modified component_A configuration" in out


def test_update_binary_archives(orchestra: OrchestraShim):
    """Checks that `orchestra update`:
    - clones binary archives that were not already cloned
    - pulls remote changes to binary archives, discarding local modifications
    """
    # --- Setup
    # Create a "remote" binary archive
    remote_binary_archive_path = orchestra.add_binary_archive("private")

    content_filename = "somefile"
    initial_content = "some content"
    remote_binary_archive_file1_path = Path(remote_binary_archive_path / content_filename)
    remote_binary_archive_file1_path.write_text(initial_content)

    git.commit_all(remote_binary_archive_path)
    remote_initial_commit_hash = git.rev_parse(remote_binary_archive_path)

    # --- Test that orchestra clones the binary archive
    orchestra("update")

    binary_archive_path = orchestra.binary_archives_dir / "private"
    binary_archive_content_path = binary_archive_path / content_filename
    assert binary_archive_path.is_dir(), "ensure the binary archive has been cloned (directory exists)"
    assert (
        git.rev_parse(binary_archive_path) == remote_initial_commit_hash
    ), "ensure the binary archive has been cloned (same commit hash)"
    assert (
        binary_archive_content_path.read_text() == initial_content
    ), "ensure the binary archive content has been cloned"

    # --- Test that orchestra pulls changes made to the binary archive
    # --- discarding local changes

    # - Modify local binary archive state
    # Modify a file that already exists
    locally_modified_content = "locally modified content"
    binary_archive_content_path.write_text(locally_modified_content)

    # Commit local changes
    git.commit_all(binary_archive_path)

    # Add a file without committing it
    spurious_file_path = binary_archive_path / "spurious_file"
    spurious_file_path.touch()

    # - Modify remote binary archive state
    remote_modified_content = "remote modified content"
    remote_binary_archive_file1_path.write_text(remote_modified_content)
    remote_commit_after_changes = git.commit_all(remote_binary_archive_path)

    # - Update
    orchestra("update")

    assert (
        git.rev_parse(binary_archive_path) == remote_commit_after_changes
    ), "ensure the binary archive HEAD been restored"
    assert (
        binary_archive_content_path.read_text() == remote_modified_content
    ), "ensure the binary archive content has been restored"


def test_update_remote_heads(orchestra: OrchestraShim):
    """Checks that `orchestra update` updates cached HEAD pointers"""
    # Register initial repository state
    remote_repository_path = orchestra.default_remote_base_url / "component_A"
    remote_initial_commit_hash = git.rev_parse(remote_repository_path)

    # Run orchestra update
    orchestra("update")

    configuration = orchestra.configuration
    branch_name = configuration.components["component_A"].branch()
    commit_hash = configuration.components["component_A"].commit()

    assert branch_name == "master"
    assert commit_hash == remote_initial_commit_hash


def test_update_pulls_repositories(orchestra: OrchestraShim):
    """Checks that `orchestra update` pulls repositories"""
    # Register initial repository state
    remote_repository_path = orchestra.default_remote_base_url / "component_A"
    content_filename = "somefile"
    remote_repository_content_path = Path(remote_repository_path / content_filename)
    initial_content = remote_repository_content_path.read_text()

    remote_initial_commit_hash = git.rev_parse(remote_repository_path)

    # Clone repository
    orchestra("clone", "component_A")
    local_repository_path = orchestra.sources_dir / "component_A"
    local_repository_content_path = local_repository_path / content_filename

    assert git.rev_parse(local_repository_path) == remote_initial_commit_hash
    assert local_repository_content_path.read_text() == initial_content

    # Modify remote repository
    modified_content = "modified content"
    remote_repository_content_path.write_text(modified_content)
    remote_modified_commit_hash = git.commit_all(remote_repository_path)

    orchestra("update")

    assert git.rev_parse(local_repository_path) == remote_modified_commit_hash
    assert local_repository_content_path.read_text() == modified_content


def test_update_does_not_overwrite_local_changes(orchestra: OrchestraShim):
    """Checks that `orchestra update` does not pulls repositories if there have been changes (only fast forwarding is
    allowed)
    """
    # Create a "remote" repository
    remote_repository_path = orchestra.default_remote_base_url / "component_A"
    content_filename = "somefile"
    remote_repository_content_path = Path(remote_repository_path / content_filename)
    initial_content = remote_repository_content_path.read_text()

    remote_initial_commit_hash = git.rev_parse(remote_repository_path)

    # Clone repository
    orchestra("clone", "component_A")
    local_repository_path = orchestra.sources_dir / "component_A"
    local_repository_content_path = local_repository_path / content_filename

    assert git.rev_parse(local_repository_path) == remote_initial_commit_hash
    assert local_repository_content_path.read_text() == initial_content

    # Modify remote repository
    remote_modified_content = "remote modified content"
    remote_repository_content_path.write_text(remote_modified_content)
    git.commit_all(remote_repository_path)

    # Modify local repository
    local_modified_content = "local modified content"
    local_repository_content_path.write_text(local_modified_content)
    local_modified_commit_hash = git.commit_all(local_repository_path)

    # update is expected to fail
    orchestra("update", should_fail=True)

    # Assert the local changes have not been discarded
    assert git.rev_parse(local_repository_path) == local_modified_commit_hash
    assert local_repository_content_path.read_text() == local_modified_content
