from .utils import git
from .data_manager import TestDataManager


class GitReposManager:
    def __init__(self, test_data_mgr):
        self._test_data_mgr: TestDataManager = test_data_mgr
        self._repos = {}

    def new_empty_repo(self, name):
        if name in self._repos:
            raise ValueError(f"{name} repo already created!")
        new_repo_path = self._test_data_mgr.newdir(name)
        git.init(new_repo_path)
        self._repos[name] = new_repo_path
        return new_repo_path

    def clone_repo(self, clone_from_name, clone_to_name):
        if clone_from_name not in self._repos:
            raise ValueError(f"{clone_from_name} is not managed by GitReposManager")
        if clone_to_name in self._repos:
            raise ValueError(f"{clone_to_name} already exists!")

    def get_repo_path(self, repo_name):
        return self._repos[repo_name]
