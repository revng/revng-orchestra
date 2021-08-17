from pathlib import Path
from typing import List, Optional, Union

from . import run_git
from ..exceptions import InternalException, InternalSubprocessException


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
    """Checks whether git-lfs is installed and raises an InternalException if it is not"""
    try:
        run_git("lfs")
        return True
    except InternalSubprocessException as e:
        raise InternalException("Could not invoke `git lfs`, is it installed?") from e
