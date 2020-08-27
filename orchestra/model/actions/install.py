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

        hard_to_symbolic = """hard-to-symbolic.py "${TMP_ROOT}${ORCHESTRA_ROOT}" """
        run_script(hard_to_symbolic, show_output=show_output, environment=self.environment)

        fix_rpath_script = dedent(f"""
        cd "$TMP_ROOT$ORCHESTRA_ROOT"
        # Fix rpath
        find . -type f -executable | while read EXECUTABLE; do
          if head -c 4 "$EXECUTABLE" | grep '^.ELF' > /dev/null && 
                file "$EXECUTABLE" | grep x86-64 | grep -E '(shared|dynamic)' > /dev/null; then
            REPLACE='$'ORIGIN/$(realpath --relative-to="$(dirname "$EXECUTABLE")" ".")
            echo "Setting rpath to $REPLACE"
            elf-replace-dynstr.py "$EXECUTABLE" "{rpath_placeholder}" "$REPLACE"
            elf-replace-dynstr.py "$EXECUTABLE" "$ORCHESTRA_ROOT" "$REPLACE"
          fi
        done
        """)
        run_script(fix_rpath_script, show_output=show_output, environment=self.environment)

        ndebug = "0"
        debug = "1" if ndebug == "0" else "0"
        patch_ndebug_script = dedent(rf"""
        cd "$TMP_ROOT$ORCHESTRA_ROOT"
        find include/ -name "*.h" \
          -exec \
            sed -i \
            -e 's|^\s*#\s*ifndef\s\+NDEBUG|#if {debug}|' \
            -e 's|^\s*#\s*ifdef\s\+NDEBUG|#if {ndebug}|' \
            -e 's|^\(\s*#\s*if\s\+.*\)!defined(NDEBUG)|\1{debug}|' \
            -e 's|^\(\s*#\s*if\s\+.*\)defined(NDEBUG)|\1{ndebug}|' \
            {"{}"} ';'
        """)
        run_script(patch_ndebug_script, show_output=show_output, environment=self.environment)

        copy_command = f'cp -farl "{tmp_root}/{orchestra_root}/." "{orchestra_root}"'
        run_script(copy_command, show_output=show_output, environment=self.environment)

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
        
        script = dedent("""
        mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/include"
        mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/lib64"
        test -e "${TMP_ROOT}${ORCHESTRA_ROOT}/lib" || ln -s lib64 "${TMP_ROOT}${ORCHESTRA_ROOT}/lib"
        test -L "${TMP_ROOT}${ORCHESTRA_ROOT}/lib"
        mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/bin"
        mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/libexec"
        """)
        
        run_script(script)

        paths_to_create = [
            "share/info",
            "share/doc",
            "share/man",
            "include",
            "lib64",
            "bin",
            "libexec",
            "lib/include",
            "lib/pkgconfig",
            "usr/lib",
            "usr/include",
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
