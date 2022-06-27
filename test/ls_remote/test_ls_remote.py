import os

from ..conftest import OrchestraShim
from ..utils import git


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


def _make_remote_ref_non_branch(orchestra: OrchestraShim, component: str):
    component_repo_path = os.path.join(orchestra.default_remote_base_url, component)
    git.run(component_repo_path, "branch", "-m", "not_master")
    git.run(component_repo_path, "update-ref", "refs/master", "HEAD")


def test_ls_remote_non_branch_remote_ref_with_local_clone(orchestra: OrchestraShim):
    """Checks that orchestra correctly reads the remote ref and commit hash when there is a local clone of the sources"""
    _make_remote_ref_non_branch(orchestra, "component_A")
    test_ls_remote_with_local_clone(orchestra)


def test_ls_remote_non_branch_remote_ref_without_local_clone(orchestra: OrchestraShim):
    """Checks that orchestra correctly reads the remote ref and commit hash when there is not a local clone of the
    sources
    """
    _make_remote_ref_non_branch(orchestra, "component_A")

    orchestra("update")

    component = orchestra.configuration.components["component_A"]
    remote_repo_path = orchestra.default_remote_base_url / "component_A"

    current_commit = git.rev_parse(remote_repo_path)

    # name-rev will always prefer the branch reference, orchestra will always prefer the configured ref name. Orchestra
    # is right in this case so the name needs to be hardcoded.
    assert component.branch() == "master"
    assert component.commit() == current_commit
