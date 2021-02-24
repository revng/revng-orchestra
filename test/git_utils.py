from subprocess import check_output


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


def init(repo_path, user="Test User", email="testuser@example.com"):
    run(repo_path, "-c", "init.defaultBranch=master", "init", "--template", "/dev/null")
    run(repo_path, "config", "--local", "user.name", user)
    run(repo_path, "config", "--local", "user.email", email)


def commit_all(repo_path, msg=None):
    if msg is None:
        msg = "Committing all changes"

    run(repo_path, "add", ".")
    run(repo_path, "commit", "-m", msg)
    return rev_parse(repo_path, ref="HEAD")


def init_lfs_for_binary_archives(repo_path):
    run(repo_path, "lfs", "track", "*.tar.*")
    run(repo_path, "add", ".gitattributes")
    run(repo_path, "commit", "-m", "Init git lfs for binary archives")


def rev_parse(repo_path, ref="master"):
    return run(repo_path, "rev-parse", ref).strip()


def run(repo_path, *args):
    return check_output(["git", "-C", repo_path, *args], encoding="utf-8")
