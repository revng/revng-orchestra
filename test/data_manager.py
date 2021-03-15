import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import List, Dict


class DataManager:
    def __init__(self, request, tmpdir):
        rootpath = request.config.rootpath
        curpath = Path(request.fspath.dirpath())
        assert curpath.is_relative_to(rootpath)
        self._search_paths: List[Path] = []
        while curpath != rootpath:
            self._search_paths.append(curpath / "data" / request.function.__name__)
            # self._search_paths.append(curpath / "data" / request.module.__name__)
            self._search_paths.append(curpath / "data")
            curpath = curpath.parent

        self._tmpdir = tmpdir

        # List of empty directories we have created
        self._new_dirs = []

        # original dirname -> list of paths where it was copied
        self._dir_copies: Dict[str, List[str]] = defaultdict(list)

    def copy(self, dirname):
        existing_copies = self._dir_copies[dirname]
        if existing_copies:
            return existing_copies[0]

        return self.copy_always(dirname)

    def copy_always(self, dirname, suffix=""):
        for search_path in self._search_paths:
            look_for = search_path / dirname
            if not look_for.exists():
                continue

            copy_to = self._tmpdir / f"{dirname}{suffix}"
            counter = 0
            while copy_to.exists():
                counter += 1
                copy_to = self._tmpdir / f"{dirname}_{counter}"

            shutil.copytree(look_for, copy_to)
            self._dir_copies[dirname].append(copy_to)
            return copy_to

        raise Exception(f"{dirname} was not found in {self._search_paths}")

    def newdir(self, prefix):
        dirpath = self._tmpdir / f"{prefix}"
        counter = 0
        while dirpath.check():
            counter += 1
            dirpath = self._tmpdir / f"{prefix}_{counter}"

        os.makedirs(dirpath, exist_ok=False)

        self._new_dirs.append(dirpath)
        return dirpath

    def get_all_copies(self, dirname):
        return self._dir_copies[dirname]
