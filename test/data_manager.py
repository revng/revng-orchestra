import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional


class TestDataManager:
    """Helper class that manages temporary data used by a test.

    The data directory/file lookup is performed as follows.
    Starting from the directory containing the test module being executed:
        - search for the requested data in "data/<test_function_name>"
        - search for the requested data in "data"
        - if not found, go one directory up
        - stop if going above the pytest "root" directory, else repeat
    """

    def __init__(self, request, tmpdir):
        rootpath = request.config.rootpath
        curpath = Path(request.fspath.dirpath())
        # is_relative_to only added in python 3.9
        try:
            curpath.relative_to(rootpath)
        except ValueError:
            raise Exception(f"{curpath} should be relative to {rootpath}")

        self._search_paths: List[Path] = []
        while curpath != rootpath:
            self._search_paths.append(curpath / "data" / request.function.__name__)
            self._search_paths.append(curpath / "data")
            curpath = curpath.parent

        self._tmpdir = tmpdir

        # List of empty directories we have created
        self._new_dirs = []

        # original dirname -> list of paths where it was copied
        self._dir_copies: Dict[str, List[str]] = defaultdict(list)

    def copy(self, name):
        """Return the path to a copy of the requested data directory or file.
        If the source data was already copied the path to the existing copy may be returned.
        """
        existing_copies = self._dir_copies[name]
        if existing_copies:
            return existing_copies[0]

        return self.copy_always(name)

    def copy_always(self, name, suffix=""):
        """Returns the path to a copy of the requested data directory or file. Always creates a new copy of the source
        data.
        """
        source_data = self._locate_source_data(name)
        if source_data is None:
            raise Exception(f"{name} was not found in {self._search_paths}")

        copy_to = self._tmpdir / f"{name}{suffix}"
        counter = 0
        while copy_to.exists():
            counter += 1
            copy_to = self._tmpdir / f"{name}_{counter}"

        shutil.copytree(source_data, copy_to)
        self._dir_copies[name].append(copy_to)
        return copy_to

    def newdir(self, prefix):
        """Creates a new uniquely named temporary directory. The name starts with the given prefix."""
        dirpath = self._tmpdir / f"{prefix}"
        counter = 0
        while dirpath.check():
            counter += 1
            dirpath = self._tmpdir / f"{prefix}_{counter}"

        os.makedirs(dirpath, exist_ok=False)

        self._new_dirs.append(dirpath)
        return dirpath

    def get_all_copies(self, name):
        """Returns a list of the paths to all the copies of the given source data directory or file"""
        return self._dir_copies[name]

    def _locate_source_data(self, name) -> Optional[Path]:
        for search_path in self._search_paths:
            look_for = search_path / name
            if look_for.exists():
                return look_for
        return None
