import os
import shutil
from pathlib import Path
from textwrap import dedent

import orchestra as orc
from orchestra.model.configuration import Configuration
from . import git_utils as git
from .data_manager import DataManager


class OrchestraShim:
    def __init__(self, test_data_mgr: DataManager, setup_default_upstream=True):
        """
        :param test_data_mgr:
        :param setup_default_upstream:
                If True an upstream configuration repository will be initialized.
                This is a full fledged repository (not a bare one) and its path
                can be accessed with the `upstream_orchestra_dir` property.

                The configuration used for running orchestra will be cloned from this
                upstream repository, so there will be a remote configured pointing to it.

                If False, only the "local" repository used for running orchestra will be initialized.
        """
        self.test_data_mgr = test_data_mgr

        if setup_default_upstream:
            # -- Create upstream repository
            # Copy test data
            tmp_upstream_orchestra_dir = test_data_mgr.copy_always("orchestra", suffix="_upstream")
            # Initialize repository
            self._initialize_orchestra_config_repo(tmp_upstream_orchestra_dir)
            # Conveniente paths
            self.upstream_orchestra_dir = Path(str(tmp_upstream_orchestra_dir))
            self.upstream_orchestra_dotdir = self.upstream_orchestra_dir / ".orchestra"

            # -- Create local orchestra directory
            tmp_orchestra_dir = test_data_mgr.newdir("orchestra")
            git.clone(tmp_upstream_orchestra_dir, tmp_orchestra_dir)
        else:
            # -- No upstream directory
            self.upstream_orchestra_dir = None
            self.upstream_orchestra_dotdir = None
            # -- Create local orchestra directory
            # Copy test data
            tmp_orchestra_dir = test_data_mgr.copy("orchestra")
            # Initialize repository
            self._initialize_orchestra_config_repo(tmp_orchestra_dir)

        # Convenience paths
        self.orchestra_dir: Path = Path(str(tmp_orchestra_dir))
        self.orchestra_root = self.orchestra_dir / "root"
        self.orchestra_dotdir = self.orchestra_dir / ".orchestra"
        self.orchestra_configdir = self.orchestra_dotdir / "config"
        self.sources_dir = self.orchestra_dir / "sources"
        self.builds_dir = self.orchestra_dir / "build"
        self.binary_archives_dir = self.orchestra_dotdir / "binary-archives"
        self.user_config = self.orchestra_configdir / "user_options.yml"

        # Setup default remote base URL and repositories
        try:
            self.default_remote_base_url = test_data_mgr.copy_always("remote_sources")
            self._init_all_subdirs_as_git_repos(self.default_remote_base_url)
        except Exception as e:
            self.default_remote_base_url = test_data_mgr.newdir(prefix="remote_sources")
        self.add_remote_base_url("default", self.default_remote_base_url)

        # Create an empty user_config.yml if not already there
        self.user_config.touch(exist_ok=True)

    def _initialize_orchestra_config_repo(self, path):
        self._add_typical_orchestra_gitignore(path)
        git.init(path)
        git.commit_all(path)

    @staticmethod
    def _init_all_subdirs_as_git_repos(path):
        path = Path(path)
        for d in os.listdir(path):
            dirpath = path / d
            if dirpath.is_dir():
                git.init(dirpath)
                git.commit_all(dirpath)

    def add_binary_archive(self, name, remote_url=None, priority="low"):
        """Add a binary archive to the configuration
        :param name: the name of the binary archive
        :param remote_url: the path to use as remote. If None a new git repository will be initialized.
        :param priority: low or high, determines if the binary archive should be considered last or first
        :return: a pathlib.Path pointing to the "remote" repository
        """
        if remote_url is None:
            remote_url = self.test_data_mgr.newdir(f"binary_archive_{name}_upstream")
            git.init(remote_url)

        overlay = dedent(
            f"""
        #@ load("@ytt:overlay", "overlay")

        #@overlay/match by=overlay.all
        ---
        #@overlay/match missing_ok=True
        binary_archives:
          #@overlay/append
          - {name}: {remote_url}
        """
        ).lstrip()

        self.add_overlay(overlay, filename_suffix="binary_archive", priority=priority)
        return remote_url

    def add_remote_base_url(self, name, url, priority="low"):
        """Add a remote base url to the configuration
        :param name: the name of the remote
        :param url: the URL of the remote
        :param priority: low or high, determines if the remote should be considered last or first
        """
        overlay = dedent(
            f"""
        #@ load("@ytt:overlay", "overlay")

        #@overlay/match by=overlay.all
        ---
        #@overlay/match missing_ok=True
        remote_base_urls:
          #@overlay/append
          - {name}: {url}
        """
        ).lstrip()

        self.add_overlay(overlay, filename_suffix="remote_base_url", priority=priority)

    def add_overlay(self, content, *, filename_suffix="overlay", priority="low"):
        if priority not in {"low", "high"}:
            raise ValueError("Priority can only be high or low")

        filename_prefix = "000" if priority == "high" else "zzz"
        n = 0
        overlay_path = self.orchestra_configdir / f"{filename_prefix}_{n}_{filename_suffix}.yml"
        while overlay_path.exists():
            n += 1
            overlay_path = self.orchestra_configdir / f"{filename_prefix}_{n}_{filename_suffix}.yml"

        with open(overlay_path, "w") as f:
            f.write(content)

    def clean_root(self):
        shutil.rmtree(self.orchestra_root)

    @staticmethod
    def _add_typical_orchestra_gitignore(orchestra_dir):
        with open(orchestra_dir / ".gitignore", "a") as f:
            f.write(
                dedent(
                    """
            root
            build
            sources
            .orchestra/tmproot
            .orchestra/binary-archives/*
            .orchestra/source_archives
            .orchestra/config_cache.yml
            .orchestra/config_cache.json
            .orchestra/remote_refs_cache.json
            .orchestra/config/user_*.yml
            .orchestra/config/000_highpriority_overlays/*
            .orchestra/config/zzz_lowpriority_overlays/*
            """
                )
            )

    def __call__(self, *args, should_fail=False):
        """
        Invokes orchestra with the given arguments, checking the return code.

        :param should_fail: if True the return code is expected to be != 0
        :param args: arguments used to invoke orchestra
        """
        args = ("--orchestra-dir", str(self.orchestra_dir)) + args
        returncode = orc._main(args)
        if should_fail:
            assert returncode != 0
        else:
            assert returncode == 0

    @property
    def configuration(self):
        return Configuration(orchestra_dotdir=self.orchestra_dotdir)
