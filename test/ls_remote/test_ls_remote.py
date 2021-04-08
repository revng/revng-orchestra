from ..utils import git
from ..conftest import OrchestraShim


def test_ls_remote_with_local_clone(orchestra: OrchestraShim):
    """Checks that orchestra correctly reads the current branch name and commit hash when there is a local clone of the
    sources
    """
    # Clone the component sources
    orchestra("clone", "component_A")

    component = orchestra.configuration.components["component_A"]
    repo_path = component.clone.environment["SOURCE_DIR"]

    new_branch_name = "new-branch"
    # Change branch
    git.run(repo_path, "checkout", "-b", new_branch_name)
    current_commit = git.rev_parse(repo_path)

    assert component.branch() == new_branch_name
    assert component.commit() == current_commit


def test_ls_remote_without_local_clone(orchestra: OrchestraShim):
    """Checks that orchestra correctly reads the current branch name and commit hash when there is not a local clone of
    the sources
    """
    orchestra("update")

    component = orchestra.configuration.components["component_A"]
    remote_repo_path = orchestra.default_remote_base_url / "component_A"

    current_commit = git.rev_parse(remote_repo_path)
    current_branch_name = git.run(remote_repo_path, "name-rev", "--name-only", "HEAD").strip()

    assert component.branch() == current_branch_name
    assert component.commit() == current_commit
