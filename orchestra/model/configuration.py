import hashlib
import json
import os
import re
import subprocess
from collections import OrderedDict
from itertools import repeat
from textwrap import dedent
from typing import Dict
from tempfile import TemporaryDirectory

import yaml
from fuzzywuzzy import fuzz
from loguru import logger

from . import build as bld
from . import component as comp
from ..actions import CloneAction, ConfigureAction, InstallAction, InstallAnyBuildAction
from ..actions.util import run_script
from ..util import parse_component_name, parse_dependency

def follow_redirects(url, max=3):
    if max == 0:
        return url

    # TODO: this code is duplicated in several places
    env = {
        "GIT_SSH_COMMAND": "ssh -oControlPath=~/.ssh/ssh-mux-%r@%h:%p -oControlMaster=auto -o ControlPersist=10",
        "GIT_LFS_SKIP_SMUDGE": "1",
    }

    new_url = None
    with TemporaryDirectory() as temporary_directory:
        # TODO: we're not printing the output
        result = run_script(f"""git clone "{url}" "{temporary_directory}" """,
                            environment=env,
                            quiet=True,
                            check_returncode=False)
        if result.returncode != 0:
            logger.info(f"Could not clone binary archive from remote {url}!")
            logger.info(result.stdout.decode("utf8").strip())
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


class Configuration:
    def __init__(self, args):
        self.args = args
        self.components: Dict[str, comp.Component] = {}
        self.from_source = args.from_source
        self.fallback_to_build = args.fallback_build

        self.orchestra_dotdir = Configuration.locate_orchestra_dotdir()
        if not self.orchestra_dotdir:
            raise Exception("Directory .orchestra not found!")

        self._create_default_user_options()

        self.generated_yaml = run_ytt(self.orchestra_dotdir, use_cache=not args.no_config_cache)
        self.parsed_yaml = yaml.safe_load(self.generated_yaml)

        self.remotes = self._get_remotes()
        self.binary_archives_remotes = self._get_binary_archives_remotes()
        self.branches = self._get_branches()

        self.orchestra_root = self.parsed_yaml.get("paths", {}).get("orchestra_root")
        if not self.orchestra_root:
            self.orchestra_root = os.path.realpath(os.path.join(self.orchestra_dotdir, "..", "root"))

        self.source_archives = self.parsed_yaml.get("paths", {}).get("source_archives")
        if not self.source_archives:
            self.source_archives = os.path.realpath(os.path.join(self.orchestra_dotdir, "source_archives"))

        self.binary_archives_dir = self.parsed_yaml.get("paths", {}).get("binary_archives")
        if not self.binary_archives_dir:
            self.binary_archives_dir = os.path.realpath(os.path.join(self.orchestra_dotdir, "binary-archives"))

        self.tmproot = self.parsed_yaml.get("paths", {}).get("tmproot")
        if not self.tmproot:
            self.tmproot = os.path.realpath(os.path.join(self.orchestra_dotdir, "tmproot"))

        self.sources_dir = self.parsed_yaml.get("paths", {}).get("sources_dir")
        if not self.sources_dir:
            self.sources_dir = os.path.realpath(os.path.join(self.orchestra_dotdir, "..", "sources"))

        self.builds_dir = self.parsed_yaml.get("paths", {}).get("builds_dir")
        if not self.builds_dir:
            self.builds_dir = os.path.realpath(os.path.join(self.orchestra_dotdir, "..", "build"))

        self._global_env = self._compute_global_env()
        self._parse_components()

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

    def installed_component_file_list_path(self, component_name):
        """
        Returns the path of the index containing the list of installed files of a component
        """
        return os.path.join(self.installed_component_metadata_dir(), component_name.replace("/", "_") + ".idx")

    def installed_component_metadata_path(self, component_name):
        """
        Returns the path of the file containing metadata about an installed component
        """
        return os.path.join(self.installed_component_metadata_dir(), component_name.replace("/", "_") + ".json")

    def installed_component_license_path(self, component_name):
        """
        Returns the path of the file containing the license of an installed component
        """
        return os.path.join(self.installed_component_metadata_dir(), component_name.replace("/", "_") + ".license")

    def installed_component_metadata_dir(self):
        """
        Returns the path of the directory containing indices of the installed components
        """
        return os.path.join(self.orchestra_root, "share", "orchestra")

    def global_env(self):
        return self._global_env.copy()

    def get_suggested_component_name(self, user_component_name):
        best_ratio = 0
        best_match = None
        for component_name in self.components:
            ratio = fuzz.ratio(user_component_name, component_name)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = component_name
        return best_match

    def _compute_global_env(self):
        env = OrderedDict()

        env["ORCHESTRA_DOTDIR"] = self.orchestra_dotdir
        env["ORCHESTRA_ROOT"] = self.orchestra_root
        env["SOURCE_ARCHIVES"] = self.source_archives
        env["BINARY_ARCHIVES"] = self.binary_archives_dir
        env["SOURCES_DIR"] = self.sources_dir
        env["BUILDS_DIR"] = self.builds_dir
        env["TMP_ROOTS"] = self.tmproot
        env["RPATH_PLACEHOLDER"] = "////////////////////////////////////////////////$ORCHESTRA_ROOT"

        # TODO: the order of the variables stays the same even if the
        #  user overrides an environment variable from the config.
        #  This is convenient but we should think if it is really what we want.
        for env_dict in self.parsed_yaml["environment"]:
            for k, v in env_dict.items():
                env[k] = v

        path = ":".join(self.parsed_yaml.get("add_to_path", []))

        for _, component in self.parsed_yaml["components"].items():
            add_to_path = component.get("add_to_path")
            if add_to_path:
                path += f":{add_to_path}"

        path += "${PATH:+:${PATH}}"
        env["PATH"] = path

        env["GIT_ASKPASS"] = "/bin/true"

        return env

    def _parse_components(self):
        # First pass: create the component, its builds and actions
        for component_name, component_yaml in self.parsed_yaml["components"].items():
            default_build = component_yaml.get("default_build")
            license = component_yaml.get("license")
            if not default_build:
                build_names = list(component_yaml["builds"])
                build_names.sort()
                default_build = build_names[0]

            skip_post_install = component_yaml.get("skip_post_install", False)
            from_source = component_yaml.get("build_from_source", False) or self.from_source
            binary_archives = component_yaml.get("binary_archives", None)
            component = comp.Component(component_name,
                                       default_build,
                                       license,
                                       from_source,
                                       binary_archives,
                                       skip_post_install=skip_post_install)

            repo = component_yaml.get("repository")
            if repo:
                clone_action = CloneAction(component, repo, self)
                component.clone = clone_action

            self.components[component_name] = component

            for build_name, build_yaml in component_yaml["builds"].items():
                ndebug = build_yaml.get("ndebug", True)
                test = build_yaml.get("test", False)

                # This will be used to compute the self_hash
                serialized_build = json.dumps(build_yaml, sort_keys=True).encode("utf-8")
                build = bld.Build(build_name,
                                  component,
                                  serialized_build,
                                  ndebug=ndebug,
                                  test=test)
                component.add_build(build)

                configure_script = build_yaml["configure"]
                build.configure = ConfigureAction(build, configure_script, self)

                install_script = build_yaml["install"]
                build.install = InstallAction(
                    build,
                    install_script,
                    self,
                    from_binary_archives=not from_source,
                    fallback_to_build=self.fallback_to_build,
                )

        # Second pass: resolve "external" dependencies
        for component_name, component_yaml in self.parsed_yaml["components"].items():
            component = self.components[component_name]

            for build_name, build_yaml in component_yaml["builds"].items():
                build = component.builds[build_name]

                dependencies = build_yaml.get("dependencies", [])
                build_dependencies = build_yaml.get("build_dependencies", [])
                # List of (dependency_name: str, build_only: bool)
                all_dependencies = []
                all_dependencies += list(zip(dependencies, repeat(False)))
                all_dependencies += list(zip(build_dependencies, repeat(True)))

                for dep, build_only in all_dependencies:
                    dep_comp_name, dep_build_name, exact_build_required = parse_dependency(dep)
                    dep_comp = self.components[dep_comp_name]

                    if dep_build_name:
                        dep_build = dep_comp.builds[dep_build_name]
                    else:
                        dep_build = dep_comp.default_build

                    if exact_build_required:
                        dep_action = dep_build.install
                    else:
                        dep_action = InstallAnyBuildAction(dep_build, self)

                    build.configure.external_dependencies.add(dep_action)
                    if not component_yaml.get("build_from_source") \
                            and not self.from_source \
                            and not build_only:
                        build.install.external_dependencies.add(dep_action)

    @staticmethod
    def locate_orchestra_dotdir(relpath=""):
        cwd = os.getcwd()
        search_path = os.path.realpath(os.path.join(cwd, relpath))
        if ".orchestra" in os.listdir(search_path):
            return os.path.join(search_path, ".orchestra")

        if search_path == "/":
            return None

        return Configuration.locate_orchestra_dotdir(os.path.join(relpath, ".."))

    @staticmethod
    def locate_user_options():
        orchestra_dotdir = Configuration.locate_orchestra_dotdir()
        return os.path.join(orchestra_dotdir, "config", "user_options.yml")

    def _create_default_user_options(self):
        remotes_config_file = Configuration.locate_user_options()
        if os.path.exists(remotes_config_file):
            return

        logger.info(f"This is the first time you run orchestra, welcome!")

        relative_path = os.path.relpath(remotes_config_file,
                                        os.path.join(self.orchestra_dotdir,
                                                     ".."))
        logger.info(f"Creating default user options in {relative_path}")
        logger.info("Populating default remotes for repositories and binary archives")
        logger.info("Remember to run `orc update` next")
        git_output = subprocess.check_output(
            ["git", "-C", self.orchestra_dotdir, "config", "--get-regexp", "remote\.[^.]*\.url"]
        ).decode("utf-8")
        remotes_re = re.compile("remote\.(?P<name>[^.]*)\.url (?P<url>.*)$")
        remotes = {}
        for line in git_output.splitlines(keepends=False):
            match = remotes_re.match(line)
            base_url = os.path.dirname(match.group("url"))
            remotes[match.group("name")] = base_url

        if not remotes:
            logger.error("Could not get default remotes, manually configure .config/user_remotes.yml")
            exit(1)

        remote_base_urls = ""
        binary_archives = ""
        for name, url in remotes.items():
            remote_base_urls += f'  - {name}: "{url}"\n'
            start_url = f"{url}/binary-archives"
            logger.info(f"Checking for redirects in {start_url}")
            binary_archives_url = follow_redirects(start_url)
            binary_archives += f'  - {name}: "{binary_archives_url}"\n'

        default_user_config = dedent("""
        #! This file was automatically generated by orchestra
        #! Edit it to suit your preferences

        #@data/values
        ---
        #@overlay/match missing_ok=True
        remote_base_urls:
        """).lstrip()
        default_user_config += remote_base_urls
        default_user_config += dedent("""
        #@overlay/match missing_ok=True
        binary_archives:
        """)
        default_user_config += binary_archives
        default_user_config += dedent("""
        #! #@overlay/replace
        #! build_from_source:
        #!   - component-name
        """)

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


def hash_config_dir(config_dir):
    hash_script = f"""find "{config_dir}" -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum"""
    config_hash = subprocess.check_output(hash_script, shell=True).decode("utf-8").strip().partition(" ")[0]
    return config_hash


def run_ytt(orchestra_dotdir, use_cache=True):
    config_dir = os.path.join(orchestra_dotdir, "config")
    config_cache_file = os.path.join(orchestra_dotdir, "config_cache.yml")
    config_hash = hash_config_dir(config_dir)

    if use_cache and os.path.exists(config_cache_file):
        with open(config_cache_file, "r") as f:
            cached_hash = f.readline().replace("#!", "").strip()
            if config_hash == cached_hash:
                return f.read()

    ytt = os.path.join(os.path.dirname(__file__), "..", "support", "ytt")
    env = os.environ.copy()
    env["GOCG"] = "off"
    expanded_yaml = subprocess.check_output(f"'{ytt}' -f {config_dir}", shell=True, env=env).decode("utf-8")

    if use_cache:
        with open(config_cache_file, "w") as f:
            f.write(f"#! {config_hash}\n")
            f.write(expanded_yaml)

    return expanded_yaml
