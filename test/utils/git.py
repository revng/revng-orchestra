import os

from subprocess import check_output
from typing import Dict


def clone(upstream_repo_path, destination):
    return check_output(
        [
            "git",
            "clone",
            # Avoids installing default hooks
            # the user might have configured
            "--template",
            "/dev/null",
            upstream_repo_path,
            destination,
        ]
    )


def init(repo_path):
    run(repo_path, "-c", "init.defaultBranch=master", "init", "--template", "/dev/null")


def commit_all(repo_path, msg=None, user="Test User", email="testuser@example.com"):
    if msg is None:
        msg = "Committing all changes"

    run(repo_path, "add", ".")
    env = {
        "GIT_AUTHOR_NAME": user,
        "GIT_COMMITTER_NAME": user,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_EMAIL": email,
    }
    run(repo_path, "commit", "-m", msg, additional_environment=env)
    return rev_parse(repo_path, ref="HEAD")


def init_lfs_for_binary_archives(repo_path):
    run(repo_path, "lfs", "track", "*.tar.*")
    run(repo_path, "add", ".gitattributes")
    run(repo_path, "commit", "-m", "Init git lfs for binary archives")


def rev_parse(repo_path, ref="master"):
    return run(repo_path, "rev-parse", ref).strip()


def run(repo_path, *args, additional_environment: Dict[str, str] = None):
    env = os.environ.copy()
    if additional_environment:
        env.update(additional_environment)
    return check_output(["git", "-C", repo_path, *args], encoding="utf-8", env=env)
