import os
import re
from collections import OrderedDict
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Dict

from fuzzywuzzy import fuzz
from loguru import logger
from pkg_resources import parse_version

from ._generate import generate_yaml_configuration, validate_configuration_schema
from ..component import Component
from ..remote_cache import RemoteHeadsCache
from ...actions.util import try_run_internal_subprocess, try_get_subprocess_output
from ...util import parse_component_name, expand_variables
from ...version import __version__, __parsed_version__


class Configuration:
    def __init__(
        self,
        fallback_to_build=False,
        force_from_source=False,
        use_config_cache=True,
        create_binary_archives=False,
        orchestra_dotdir=None,
        no_merge=False,
        keep_tmproot=False,
        run_tests=False,
    ):
        self.components: Dict[str, Component] = {}

        # Allows to trigger a build from source if binary archives are not found
        self.fallback_to_build = fallback_to_build

        # Forces all components to be built from source
        self.build_all_from_source = force_from_source

        # Enables creation of binary archives for all install actions that get run
        self.create_binary_archives = create_binary_archives

        # Disables merging files into orchestra root after building
        # Useful for debugging a broken component without touching orchestra root
        self.no_merge = no_merge

        # Disables removal of the temporary root directory
        self.keep_tmproot = keep_tmproot

        # Enables tests when building components from source
        self.run_tests = run_tests

        self.orchestra_dotdir = locate_orchestra_dotdir(cwd=orchestra_dotdir)
        if not self.orchestra_dotdir:
            raise Exception("Directory .orchestra not found!")

        self._create_default_user_options()
        self.parsed_yaml = generate_yaml_configuration(self.orchestra_dotdir, use_cache=use_config_cache)

        self._check_minimum_version()

        validate_configuration_schema(self.parsed_yaml)

        self.remotes = self._get_remotes()
        self.binary_archives_remotes = self._get_binary_archives_remotes()
        self.branches = self._get_branches()

        self._user_paths = self.parsed_yaml.get("paths", {})

        remote_heads_cache_path = os.path.join(self.orchestra_dotdir, "remote_refs_cache.json")
        self.remote_heads_cache = RemoteHeadsCache(self, remote_heads_cache_path)

        self._initialize_paths()
        self._parse_components()

    def _initialize_paths(self):
        """Initialized various paths used by orchestra and passed to the user scripts.
        The paths are guaranteed to be absolute
        """
        # Orchestra root directory. All components will be installed here
        self.orchestra_root = self._get_user_path("orchestra_root", os.path.join("..", "root"))
        # Directory containing cached source archives
        self.source_archives = self._get_user_path("source_archives", "source_archives")
        # Directory containing binary archives repositories
        self.binary_archives_dir = self._get_user_path("binary_archives", "binary-archives")
        # Directory containing temporary roots
        self.tmproot = self._get_user_path("tmproot", "tmproot")
        # Directory containing the source directories
        self.sources_dir = self._get_user_path("sources_dir", os.path.join("..", "sources"))
        # Directory containing the build directories
        self.builds_dir = self._get_user_path("builds_dir", os.path.join("..", "build"))
        # Directory containing metadata for the installed components
        self.installed_component_metadata_dir = os.path.join(self.orchestra_root, "share", "orchestra")

        # Dictionary of binary archive name -> local path where the binary archive repo is cloned
        self.binary_archives_local_paths = {
            name: os.path.join(self.binary_archives_dir, name) for name in self.binary_archives_remotes
        }

    def get_build(self, comp_spec):
        component_name, build_name = parse_component_name(comp_spec)
        component = self.components.get(component_name)
        if not component:
            return None
        if build_name:
            build = component.builds[build_name]
        else:
            build = component.default_build
        return build

    def global_env(self) -> "OrderedDict[str, str]":
        env = OrderedDict()
        env["ORCHESTRA_DOTDIR"] = self.orchestra_dotdir
        env["ORCHESTRA_ROOT"] = self.orchestra_root
        env["SOURCE_ARCHIVES"] = self.source_archives
        env["BINARY_ARCHIVES"] = self.binary_archives_dir
        env["SOURCES_DIR"] = self.sources_dir
        env["BUILDS_DIR"] = self.builds_dir
        env["TMP_ROOTS"] = self.tmproot
        env["RPATH_PLACEHOLDER"] = "////////////////////////////////////////////////$ORCHESTRA_ROOT"
        env["GIT_ASKPASS"] = "/bin/true"

        # TODO: the order of the variables stays the same even if the user overrides an
        #       environment variable from the config. This is convenient but we should
        #       think if it is really what we want.
        for env_dict in self.parsed_yaml.get("environment", {}):
            for k, v in env_dict.items():
                env[k] = v

        path = ":".join(self.parsed_yaml.get("add_to_path", []))

        for component in self.components.values():
            for additional_path in component.add_to_path:
                path += f":{additional_path}"

        path += "${PATH:+:${PATH}}"
        env["PATH"] = path

        return env

    def get_suggested_component_name(self, user_component_name):
        best_ratio = 0
        best_match = None
        for component_name in self.components:
            ratio = fuzz.ratio(user_component_name, component_name)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = component_name
        return best_match

    def _parse_components(self):
        # First pass: create the components, their builds and actions
        for component_name, component_yaml in self.parsed_yaml["components"].items():
            component = Component(component_name, component_yaml, self)
            self.components[component_name] = component

        # Second pass: resolve dependencies
        for component in self.components.values():
            component.resolve_dependencies(self)

    def _check_minimum_version(self):
        min_version = self.parsed_yaml.get("min_orchestra_version")
        if min_version:
            parsed_min_version = parse_version(min_version)
            if __parsed_version__ < parsed_min_version:
                raise Exception(
                    f"This configuration requires orchestra version >= {min_version}, you have {__version__}"
                )

    def _create_default_user_options(self):
        remotes_config_file = self.user_options_path
        if os.path.exists(remotes_config_file):
            return

        logger.info(f"This is the first time you run orchestra, welcome!")

        relative_path = os.path.relpath(remotes_config_file, os.path.join(self.orchestra_dotdir, ".."))
        logger.info(f"Creating default user options in {relative_path}")
        logger.info("Populating default remotes for repositories and binary archives")
        logger.info("Remember to run `orc update` next")

        git_output = try_get_subprocess_output(
            [
                "git",
                "-C",
                self.orchestra_dotdir,
                "config",
                "--get-regexp",
                r"remote\.[^.]*\.url",
            ]
        )
        if git_output is None:
            logger.error(f"Could not get default remotes, manually configure {relative_path}")
            exit(1)

        remotes_re = re.compile(r"remote\.(?P<name>[^.]*)\.url (?P<url>.*)$")

        remotes = {}
        for line in git_output.splitlines(keepends=False):
            match = remotes_re.match(line)
            base_url = os.path.dirname(match.group("url"))
            remotes[match.group("name")] = base_url

        if not remotes:
            logger.error(f"Could not get default remotes, manually configure {relative_path}")
            exit(1)

        remote_base_urls = ""
        binary_archives = ""
        for name, url in remotes.items():
            remote_base_urls += f'  - {name}: "{url}"\n'
            start_url = f"{url}/binary-archives"
            logger.info(f"Checking for redirects in {start_url}")
            binary_archives_url = follow_redirects(start_url)
            binary_archives += f'  - {name}: "{binary_archives_url}"\n'

        default_user_config = dedent(
            """
            #! This file was automatically generated by orchestra
            #! Edit it to suit your preferences

            #@data/values
            ---
            #@overlay/match missing_ok=True
            remote_base_urls:
            """
        ).lstrip()
        default_user_config += remote_base_urls

        default_user_config += dedent(
            """
            #@overlay/match missing_ok=True
            binary_archives:
            """
        )
        default_user_config += binary_archives
        default_user_config += dedent(
            """
            #! #@overlay/replace
            #! build_from_source:
            #!   - component-name
            """
        )

        with open(remotes_config_file, "w") as f:
            f.write(default_user_config)

    def _get_remotes(self):
        remotes = OrderedDict()
        for remote in self.parsed_yaml.get("remote_base_urls", []):
            assert len(remote) == 1, "remote_base_urls must be a list of dictionaries with one entry (name: url)"
            for name, url in remote.items():
                remotes[name] = url
        return remotes

    def _get_binary_archives_remotes(self):
        remotes = OrderedDict()
        for remote in self.parsed_yaml.get("binary_archives", []):
            assert len(remote) == 1, "binary_archives must be a list of dictionaries with one entry (name: url)"
            for name, url in remote.items():
                remotes[name] = url
        return remotes

    def _get_branches(self):
        branches = self.parsed_yaml.get("branches", [])
        assert type(branches) is list
        for branch in branches:
            assert type(branch) is str, "branches must be a list of strings"
        return branches

    def _get_user_path(self, name, default):
        """Returns a user-configured path after variable expansion and relative path resolution.
        If the user did not configure the requested path the default is used. After determining the initial path
        environment variables are expanded. Relative are evaluated relative to `$ORCHESTRA_DOTDIR`
        """
        path = self._user_paths.get(name, default)
        path = expand_variables(path)
        if not os.path.isabs(path):
            path = os.path.join(self.orchestra_dotdir, path)
        path = os.path.realpath(path)
        return path

    @property
    def user_options_path(self):
        return os.path.join(self.orchestra_dotdir, "config", "user_options.yml")

    def _expand_variables(self, string):
        """Expands environment variables found in string using the system and orchestra environment"""
        return expand_variables(string, additional_environment=self.global_env())


def locate_orchestra_dotdir(cwd=None):
    if cwd is None:
        cwd = os.getcwd()

    while cwd != "/":
        path_to_try = os.path.join(cwd, ".orchestra")
        if os.path.isdir(path_to_try):
            return path_to_try
        cwd = os.path.realpath(os.path.join(cwd, ".."))

    return None


def follow_redirects(url, max=3):
    """Recursively follows REDIRECT files found in a repository (up to `max` depth)"""
    if max == 0:
        return url

    # TODO: this code is duplicated in several places
    env = os.environ.copy()
    env.update(
        {
            "GIT_SSH_COMMAND": "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10",
            "GIT_LFS_SKIP_SMUDGE": "1",
        }
    )

    new_url = None
    with TemporaryDirectory() as temporary_directory:
        returncode = try_run_internal_subprocess(
            ["git", "clone", "--depth", "1", url, temporary_directory],
            environment=env,
        )
        if returncode != 0:
            logger.info(f"Could not clone binary archive from remote {url}!")
            return url

        redirect_path = os.path.join(temporary_directory, "REDIRECT")
        if os.path.exists(redirect_path):
            with open(redirect_path) as redirect_file:
                new_url = redirect_file.read().strip()

    if new_url:
        logger.info(f"Redirecting to {new_url}")
        return follow_redirects(new_url, max - 1)
    else:
        return url
