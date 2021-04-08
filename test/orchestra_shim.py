import os
import shutil
from pathlib import Path
from textwrap import dedent

import orchestra as orc
from orchestra.model.configuration import Configuration
from .utils import git
from .data_manager import TestDataManager


class OrchestraShim:
    def __init__(self, test_data_mgr: TestDataManager, setup_default_upstream=True):
        """This constructor is not meant to be called directly. Request the `orchestra` fixture instead.
        To pass parameters use the pytest marks functionality (see the `orchestra` fixture docstring).

        When called, a directory called `orchestra` will be requested from the `TestDataManager`, which will be expected
        to contain a template for the configuration used to run orchestra.
        This template will be initialized as a git repository (see the `setup_default_upstream` parameter docstring).

        A directory called `remote_sources` will also be requested from the `TestDataManager`. If it is found, all the
        subdirectories contained within `remote_sources` will be initialized as git repositories, and `remote_sources`
        will be included as the default `remote_base_url`.

        If the template directory does not contain a `.orchestra/config/user_options.yml` file an empty one will be
        automatically created.

        :param test_data_mgr: a TestDataManager instance
        :param setup_default_upstream:
               If False, only the "local" repository used for running orchestra will be initialized from the template
               data.

               If True a "remote" upstream configuration repository will be created from the template data, and the
               local configuration used for running orchestra will be cloned from that.
               This upstream repository will be placed on a locally accessible path that will contain a checkout of the
               `master` worktree.
               The local configuration will have a remote pointing to the "remote" configuration.
               The remote repository path can be accessed with the `upstream_orchestra_dir` property.
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

        # Overlays added at runtime and managed by this class
        self._overlays = set()

        # Setup default remote base URL and repositories
        try:
            self.default_remote_base_url = test_data_mgr.copy_always("remote_sources")
            self._init_all_subdirs_as_git_repos(self.default_remote_base_url)
        except Exception:
            self.default_remote_base_url = test_data_mgr.newdir(prefix="remote_sources")
        self.add_remote_base_url("default", self.default_remote_base_url)

        # Create an empty user_config.yml if not already there
        self.user_config.touch(exist_ok=True)

    def __call__(self, *args, should_fail=False):
        """
        Invokes orchestra with the given cmdline arguments, checking the return code.

        :param should_fail: if True the return code is expected to be != 0
        :param args: arguments used to invoke orchestra
        """
        args = ("--orchestra-dir", str(self.orchestra_dir)) + args
        returncode = orc._main(args)
        if should_fail:
            assert returncode != 0
        else:
            assert returncode == 0

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
        :returns an overlay handle
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

        return self.add_overlay(overlay, filename_suffix="remote_base_url", priority=priority)

    def add_overlay(self, content, *, filename_suffix="overlay", priority="low"):
        """Adds an overlay to the configuration
        :param content: the overlay content
        :param filename_suffix: an optional suffix for the overlay name, useful for debugging or ordering overlays with
               the same priority (overlays are processed in alphabetical order)
        :param priority: either "low" or "high", determines the order in which overlays are processed.
               High priority overlays are processed first
        :returns a handle that can be passed to `remove_overlay`
        """
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

        self._overlays.add(overlay_path)
        return overlay_path

    def remove_overlay(self, handle):
        """Removes an overlay identified by `handle`
        :param handle: an overlay handle
        """
        if handle not in self._overlays:
            raise ValueError("Asked to remove an overlay which is not managed by this object")
        Path(handle).unlink()
        self._overlays.remove(handle)

    def set_environment_variable(self, name, value, priority="low"):
        """Adds an overlay that sets an environment variable
        :param name: the name of the environment variable to set
        :param value: the value the variable hash to be set to
        :param priority: either "low" or "high", same meaning of `add_overlay`
        :returns an overlay handle
        """
        return self.add_overlay(
            dedent(
                f"""
                #@ load("@ytt:overlay", "overlay")
                #@overlay/match by=overlay.all, missing_ok=True
                #@overlay/match-child-defaults missing_ok=True
                ---
                environment: 
                    #@overlay/append
                    - "{name}": "{value}"
                """
            ),
            priority=priority,
            filename_suffix="environment",
        )

    def unset_environment_variable(self, name, priority="low"):
        """Adds an overlay that unsets an environment variable
        :param name: the name of the environment variable to unset
        :param priority: either "low" or "high", same meaning of `add_overlay`
        :returns an overlay handle
        """
        return self.set_environment_variable(f"-{name}", "", priority=priority)

    @property
    def configuration(self):
        """Returns a Configuration object created from `orchestra_dotdir`.
        Note: This is **not** the same object used when running orchestra, so modifying its properties will have no
              effect on orchestra execution.
        """
        return Configuration(orchestra_dotdir=self.orchestra_dotdir)

    def clean_root(self):
        """Deletes the orchestra root directory"""
        shutil.rmtree(self.orchestra_root)

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

    @staticmethod
    def _add_typical_orchestra_gitignore(orchestra_dir):
        typical_gitignore = dedent(
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

        with open(orchestra_dir / ".gitignore", "a") as f:
            f.write(typical_gitignore)
