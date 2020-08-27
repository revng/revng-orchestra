import glob
import os
import shutil
from collections import OrderedDict
from textwrap import dedent

from .action import Action
from .util import run_script
from ...environment import global_env, per_action_env
from ...util import install_component_dir, install_component_path, is_installed


class InstallAction(Action):
    def __init__(self, build, script, index):
        super().__init__("install", build, script, index)

    def _run(self, show_output=False):
        genv = global_env(self.index.config)
        tmp_root = genv["TMP_ROOT"]
        orchestra_root = genv['ORCHESTRA_ROOT']
        rpath_placeholder = self.index.config["options"]["rpath_placeholder"]

        self._prepare_tmproot()
        pre_file_list = self._index_directory(tmp_root, strip_prefix=tmp_root + orchestra_root)

        run_script(self.script, show_output=show_output, environment=self.environment)

        post_file_list = self._index_directory(tmp_root, strip_prefix=tmp_root + orchestra_root)
        new_files = [f for f in post_file_list if f not in pre_file_list]

        # TODO: uninstall the currently installed build of this component if there's one
        # TODO: do all the stuff that install-in-temp did (see string below)
        """
        rm -rf "$(TEMP_INSTALL_PATH)"
        mkdir -p "$(TEMP_INSTALL_PATH)"
        make install-impl-$($(1)_TARGET_NAME) "DESTDIR=$(TEMP_INSTALL_PATH)"
        cd "$(TEMP_INSTALL_PATH)/$(INSTALL_PATH)"
        $(PWD)/support/hard-to-symbolic.py .
        mkdir -p "share/orchestra"
        mkdir -p $$$$(dirname "share/orchestra/$($(6)_TARGET_NAME)")
        find . -mindepth 1 -not -type d -not -path ./lib > "share/orchestra/$($(6)_TARGET_NAME)"
        find . -type f -executable | while read EXECUTABLE; do \
          if head -c 4 "$$$$EXECUTABLE" | grep '^.ELF' > /dev/null && file "$$$$EXECUTABLE" | grep x86-64 | grep -E '(shared|dynamic)' > /dev/null; then \
            $(call log-info,"$$$$EXECUTABLE is an ELF for the host") \
            REPLACE='$$$$'ORIGIN/$$$$(realpath --relative-to="$$$$(dirname $$$$EXECUTABLE)" ".")
            echo "Setting rpath to $$$$REPLACE"
            $(PWD)/support/elf-replace-dynstr.py "$$$$EXECUTABLE" $(RPATH_PLACEHOLDER) "$$$$REPLACE" /
            $(PWD)/support/elf-replace-dynstr.py "$$$$EXECUTABLE" $(INSTALL_PATH) "$$$$REPLACE" /
          fi
        done
    
        $(call log-info,"Patching NDEBUG in include/*.h")
        find include/ \
          -name "*.h" \
          -exec \
            sed -i \
            -e 's|^\s*#\s*ifndef\s\+NDEBUG|#if $(if $(filter 1,$($(1)_NDEBUG)),0,1)|' \
            -e 's|^\s*#\s*ifdef\s\+NDEBUG|#if $($(1)_NDEBUG)|' \
            -e 's|^\(\s*#\s*if\s\+.*\)!defined(NDEBUG)|\1$(if $(filter 1,$($(1)_NDEBUG)),0,1)|' \
            -e 's|^\(\s*#\s*if\s\+.*\)defined(NDEBUG)|\1$($(1)_NDEBUG)|' \
            {} \;
        """

        copy_command = f'cp -farl "{genv["TMP_ROOT"]}/{genv["ORCHESTRA_ROOT"]}/." "{genv["ORCHESTRA_ROOT"]}"'
        result = run_script(copy_command, show_output=show_output)
        if result.returncode != 0:
            logging.error(f"Subprocess exited with exit code {result.returncode}")
            logging.error(f"Script executed: {copy_command}")
            logging.error(f"STDOUT: {result.stdout}")
            logging.error(f"STDERR: {result.stderr}")
            raise Exception("Post-install script failed (might be a bug in Orchestra)")

        os.makedirs(install_component_dir(self.index.config), exist_ok=True)
        installed_component_path = install_component_path(self.build.component.name, self.index.config)
        with open(installed_component_path, "w") as f:
            f.truncate(0)
            f.write(self.build.qualified_name + "\n")
            f.write("\n".join(new_files))

    def is_satisfied(self):
        return is_installed(self.index.config, self.build.component.name, wanted_build=self.build.name)

    def _prepare_tmproot(self):
        tmp_root = global_env(self.index.config)["TMP_ROOT"]
        orchestra_root = global_env(self.index.config)["ORCHESTRA_ROOT"]
        shutil.rmtree(tmp_root, ignore_errors=True)
        os.makedirs(tmp_root, exist_ok=True)

        paths_to_create = [
            "bin",
            "share/info",
            "share/doc",
            "share/man",
            "libexec",
            "lib64",
            "lib/include",
            "lib/pkgconfig",
            "usr/lib",
            "usr/include",
            "include",
        ]
        for p in paths_to_create:
            os.makedirs(f"{tmp_root}/{orchestra_root}/{p}", exist_ok=True)

    @staticmethod
    def _index_directory(dirpath, strip_prefix=None):
        paths = list(glob.glob(f"{dirpath}/**", recursive=True))
        if strip_prefix:
            paths = [p.lstrip(strip_prefix) for p in paths]
        return paths

    @property
    def environment(self) -> OrderedDict:
        env = per_action_env(self)
        env["DESTDIR"] = env["TMP_ROOT"]
        return env
