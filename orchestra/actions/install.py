import glob
import json
import time
import os
from collections import OrderedDict
from loguru import logger
from textwrap import dedent

from .action import Action
from .util import run_script
from ..util import is_installed, get_installed_build


class InstallAction(Action):
    def __init__(self, build, script, config, from_binary_archives=False, fallback_to_build=False):
        name = "install"
        name += " from binary archives" if from_binary_archives else ""
        name += " with fallback" if from_binary_archives and fallback_to_build else ""
        super().__init__(name, build, script, config)
        self.from_binary_archives = from_binary_archives
        self.fallback_to_build = fallback_to_build

    def _run(self, args):
        environment = self.config.global_env()
        tmp_root = environment["TMP_ROOT"]
        orchestra_root = environment['ORCHESTRA_ROOT']

        logger.info("Preparing temporary root directory")
        self._prepare_tmproot()
        pre_file_list = self._index_directory(tmp_root + orchestra_root, strip_prefix=tmp_root + orchestra_root)

        start_time = time.time()

        if self.from_binary_archives and self._binary_archive_exists():
            self._fetch_binary_archive()
            self._install_from_binary_archives()
        elif not self.from_binary_archives or self.fallback_to_build:
            self._install(args.quiet)
            self._post_install(args.quiet)
        else:
            raise Exception("Binary archive not found!")

        end_time = time.time()

        post_file_list = self._index_directory(tmp_root + orchestra_root, strip_prefix=tmp_root + orchestra_root)
        new_files = [f for f in post_file_list if f not in pre_file_list]

        archive_name = self.build.binary_archive_filename
        archive_path = os.path.join(self.environment["BINARY_ARCHIVES"], archive_name)
        if args.create_binary_archives and not os.path.exists(archive_path):
            logger.info("Creating binary archive")
            self._create_binary_archive()

        if args.no_merge:
            return

        self._uninstall_currently_installed_build(args.quiet)

        logger.info("Merging installation into Orchestra root directory")
        self._merge(args.quiet)

        # Write file metadata and index
        os.makedirs(self.config.installed_component_metadata_dir(), exist_ok=True)
        metadata = {
            "component_name": self.build.component.name,
            "build_name": self.build.name,
            "install_time": end_time - start_time,
        }
        with open(self.config.installed_component_metadata_path(self.build.component.name), "w") as f:
            json.dump(metadata, f)
        with open(self.config.installed_component_file_list_path(self.build.component.name), "w") as f:
            f.truncate(0)
            new_files = [f"{f}\n" for f in new_files]
            f.writelines(new_files)

        if not args.keep_tmproot:
            logger.info("Cleaning up tmproot")
            self._cleanup_tmproot()

    def _is_satisfied(self):
        return is_installed(self.config, self.build.component.name, wanted_build=self.build.name)

    def _prepare_tmproot(self):
        script = dedent("""
            rm -rf "$TMP_ROOT"
            mkdir -p "$TMP_ROOT"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/include"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/lib64"{,/include,/pkgconfig}
            test -e "${TMP_ROOT}${ORCHESTRA_ROOT}/lib" || ln -s lib64 "${TMP_ROOT}${ORCHESTRA_ROOT}/lib"
            test -L "${TMP_ROOT}${ORCHESTRA_ROOT}/lib"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/bin"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/usr/"{lib,include}
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/share/"{info,doc,man}
            touch "${TMP_ROOT}${ORCHESTRA_ROOT}/share/info/dir"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/libexec"
            """)
        run_script(script, environment=self.environment, quiet=True)

    def _cleanup_tmproot(self):
        run_script('rm -rf "$TMP_ROOT"', environment=self.environment, quiet=True)

    def _install(self, quiet):
        logger.info("Executing install script")
        run_script(self.script, quiet=quiet, environment=self.environment)

    def _post_install(self, quiet):
        # TODO: maybe this should be put into the configuration and not in Orchestra itself
        logger.info("Converting hardlinks to symbolic")
        self._hard_to_symbolic(quiet)

        # TODO: maybe this should be put into the configuration and not in Orchestra itself
        logger.info("Fixing RPATHs")
        self._fix_rpath(quiet)

        # TODO: this should be put into the configuration and not in Orchestra itself
        logger.info("Replacing NDEBUG preprocessor statements")
        self._replace_ndebug(True, quiet)

    def _hard_to_symbolic(self, quiet):
        hard_to_symbolic = """hard-to-symbolic.py "${TMP_ROOT}${ORCHESTRA_ROOT}" """
        run_script(hard_to_symbolic, quiet=quiet, environment=self.environment)

    def _fix_rpath(self, quiet):
        fix_rpath_script = dedent(f"""
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            # Fix rpath
            find . -type f -executable | while read EXECUTABLE; do
                if head -c 4 "$EXECUTABLE" | grep '^.ELF' > /dev/null &&
                        file "$EXECUTABLE" | grep x86-64 | grep -E '(shared|dynamic)' > /dev/null;
                then
                    REPLACE='$'ORIGIN/$(realpath --relative-to="$(dirname "$EXECUTABLE")" ".")
                    echo "Setting rpath of $EXECUTABLE to $REPLACE"
                    elf-replace-dynstr.py "$EXECUTABLE" "$RPATH_PLACEHOLDER" "$REPLACE" /
                    elf-replace-dynstr.py "$EXECUTABLE" "$ORCHESTRA_ROOT" "$REPLACE" /
                fi
            done
            """)
        run_script(fix_rpath_script, quiet=quiet, environment=self.environment)

    def _replace_ndebug(self, enable_debugging, quiet):
        debug, ndebug = ("1", "0") if enable_debugging else ("0", "1")
        patch_ndebug_script = dedent(rf"""
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            find include/ -name "*.h" \
                -exec \
                    sed -i \
                    -e 's|^\s*#\s*ifndef\s\+NDEBUG|#if {debug}|' \
                    -e 's|^\s*#\s*ifdef\s\+NDEBUG|#if {ndebug}|' \
                    -e 's|^\(\s*#\s*if\s\+.*\)!defined(NDEBUG)|\1{debug}|' \
                    -e 's|^\(\s*#\s*if\s\+.*\)defined(NDEBUG)|\1{ndebug}|' \
                    {{}} ';'
            """)
        run_script(patch_ndebug_script, quiet=quiet, environment=self.environment)

    def _uninstall_currently_installed_build(self, quiet):
        installed_build = get_installed_build(self.build.component.name, self.config)

        if installed_build is None:
            return

        logger.info("Uninstalling previously installed build")
        uninstall(self.build.component.name, self.config)

    def _merge(self, quiet):
        copy_command = f'cp -farl "$TMP_ROOT/$ORCHESTRA_ROOT/." "$ORCHESTRA_ROOT"'
        run_script(copy_command, quiet=quiet, environment=self.environment)

    def _create_binary_archive(self):
        archive_name = self.build.binary_archive_filename
        script = dedent(f"""
            mkdir -p "$BINARY_ARCHIVES"
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            tar caf "$BINARY_ARCHIVES/{archive_name}" --owner=0 --group=0 "."
            """)
        run_script(script, quiet=True, environment=self.environment)

    def _binary_archive_filepath(self):
        archives_dir = self.environment["BINARY_ARCHIVES"]
        return os.path.join(archives_dir, self.build.binary_archive_filename)

    def _binary_archive_exists(self):
        archive_filepath = self._binary_archive_filepath()
        return os.path.exists(archive_filepath)

    def _fetch_binary_archive(self):
        script = dedent(f'''
            cd "$BINARY_ARCHIVES"
            python $ORCHESTRA_DOTDIR/helpers/git-lfs --only "$(readlink -f "{self._binary_archive_filepath()}")"
            ''')
        run_script(script, quiet=True, environment=self.environment)

    def _install_from_binary_archives(self):
        if not self._binary_archive_exists():
            raise Exception("Binary archive not found!")

        archive_filepath = self._binary_archive_filepath()
        script = dedent(f"""
            mkdir -p "$TMP_ROOT$ORCHESTRA_ROOT"
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            tar xaf "{archive_filepath}"
            """)
        run_script(script, environment=self.environment, quiet=True)

    @staticmethod
    def _index_directory(dirpath, strip_prefix=None):
        paths = list(glob.glob(f"{dirpath}/**", recursive=True))
        if strip_prefix:
            paths = [remove_prefix(p, strip_prefix) for p in paths]
        return paths

    @property
    def environment(self) -> OrderedDict:
        env = super().environment
        env["TMP_ROOT"] = os.path.join(env["TMP_ROOT"], self.build.safe_name)
        env["DESTDIR"] = env["TMP_ROOT"]
        return env

    def _implicit_dependencies(self):
        if self.from_binary_archives and (self._binary_archive_exists() or not self.fallback_to_build):
            return set()
        else:
            return {self.build.configure}


class InstallAnyBuildAction(Action):
    def __init__(self, build, config):
        installed_build_name = get_installed_build(build.component.name, config)
        if installed_build_name:
            chosen_build = build.component.builds[installed_build_name]
        else:
            chosen_build = build
        super().__init__("install any", chosen_build, None, config)
        self._original_build = build

    def _implicit_dependencies(self):
        return {self.build.install}

    def _run(self, args):
        return

    def is_satisfied(self, recursively=False, already_checked=None):
        return any(
            build.install.is_satisfied(recursively=recursively, already_checked=already_checked)
            for build in self.build.component.builds.values()
            )

    def _is_satisfied(self):
        raise NotImplementedError("This method should not be called!")

    @property
    def name_for_graph(self):
        if self.build == self._original_build:
            return f"install {self.build.component.name} (prefer {self._original_build.name})"
        else:
            return f"install {self.build.component.name} (prefer {self._original_build.name}, chosen {self.build.name})"

    @property
    def name_for_components(self):
        return f"{self._original_build.component.name}~{self._original_build.name}"


def remove_prefix(string, prefix):
    if string.startswith(prefix):
        return string[len(prefix):]
    else:
        return string[:]


def uninstall(component_name, config):
    index_path = config.installed_component_file_list_path(component_name)
    metadata_path = config.installed_component_metadata_path(component_name)

    with open(index_path) as f:
        paths = f.readlines()

    # Ensure depth first visit by reverse-sorting
    paths.sort(reverse=True)
    paths = [path.strip() for path in paths]

    for path in paths:
        path = path.lstrip("/")
        path_to_delete = os.path.join(config.global_env()['ORCHESTRA_ROOT'], path)
        if os.path.isfile(path_to_delete) or os.path.islink(path_to_delete):
            logger.debug(f"Deleting {path_to_delete}")
            os.remove(path_to_delete)
        elif os.path.isdir(path_to_delete):
            if os.listdir(path_to_delete):
                logger.debug(f"Not removing directory {path_to_delete} as it is not empty")
            else:
                logger.debug(f"Deleting directory {path_to_delete}")
                os.rmdir(path_to_delete)

    logger.debug(f"Deleting index file {index_path}")
    os.remove(index_path)

    logger.debug(f"Deleting metadata file {metadata_path}")
    os.remove(metadata_path)
