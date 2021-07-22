from pathlib import Path
from typing import List, Optional, Union

from . import run_git
from ..exceptions import UserException, InternalSubprocessException


_lfs_install_checked = False


def fetch(
    workdir,
    checkout=True,
    include: Optional[List[Union[str, Path]]] = None,
):
    """
    Fetch (and checkout) git lfs tracked files
    :param workdir: path to the working directory
    :param checkout: if True (default), the files are also checked out so their content matches the one tracked by LFS
    :param include: optional list of paths to fetch. Paths must be relative to the repository root. Some shell
             expansions are supported (e.g. *.tar.gz), see `man git-lfs-fetch`.
    """
    assert_lfs_installed()

    if include is None:
        include = []

    fetch_cmd = [
        "lfs",
        "fetch",
    ]
    if include:
        fetch_cmd.append("--include")
        fetch_cmd.append(",".join(str(i) for i in include))
    run_git(*fetch_cmd, workdir=workdir)

    if not checkout:
        return

    checkout_cmd = [
        "lfs",
        "checkout",
    ]
    for include_file in include:
        checkout_cmd.append(str(include_file))
    run_git(*checkout_cmd, workdir=workdir)


def assert_lfs_installed():
    """Checks whether git-lfs is installed and raises an OrchestraException if it is not"""
    global _lfs_install_checked

    if _lfs_install_checked:
        return True

    try:
        run_git("lfs")
    except InternalSubprocessException:
        raise UserException("Could not invoke `git lfs`, is it installed?")

    try:
        run_git("config", "--get", "filter.lfs.smudge")
    except InternalSubprocessException:
        raise UserException("GIT LFS does not seem to be installed properly. Run `git lfs install`.")

    _lfs_install_checked = True

    return True
