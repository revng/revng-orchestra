import glob
import os
import pathlib
import shutil
import stat
import time
from collections import OrderedDict, defaultdict
from pathlib import Path
from textwrap import dedent
from typing import Iterable, List, Optional

from loguru import logger

from .action import ActionForBuild
from .uninstall import uninstall
from .util import run_user_script
from ..exceptions import (
    BinaryArchiveNotFoundException,
    InternalCommandException,
    InternalSubprocessException,
    UserException,
)
from ..gitutils import lfs
from ..gitutils import get_worktree_root
from ..model.install_metadata import (
    load_metadata,
    init_metadata_from_build,
    save_metadata,
    save_file_list,
    is_installed,
    installed_component_license_path,
    installed_component_file_list_path,
    installed_component_metadata_path,
)


class InstallAction(ActionForBuild):
    def __init__(
        self,
        build,
        script,
        config,
        allow_build=True,
        allow_binary_archive=True,
        create_binary_archive=False,
        no_merge=False,
        keep_tmproot=False,
        run_tests=False,
        discard_build_directories=False,
    ):
        assert (
            allow_build or allow_binary_archive
        ), f"You must allow at least one option between building and installing from binary archives for {build.name}"
        sources = []
        if allow_build:
            sources.append("build")
        if allow_binary_archive:
            sources.append("binary archives")
        sources_str = " or ".join(sources)

        super().__init__(f"install ({sources_str})", build, script, config)
        self.allow_build = allow_build
        self.allow_binary_archive = allow_binary_archive
        self.create_binary_archive = create_binary_archive
        self.no_merge = no_merge
        self.keep_tmproot = keep_tmproot
        self.run_tests = run_tests
        self.discard_build_directories = discard_build_directories

    def _run(self, explicitly_requested=False):
        tmp_root = self.environment["TMP_ROOT"]
        orchestra_root = self.environment["ORCHESTRA_ROOT"]

        logger.debug("Preparing temporary root directory")
        self._prepare_tmproot()

        pre_file_list = self._index_directory(tmp_root + orchestra_root, relative_to=tmp_root + orchestra_root)

        install_start_time = time.time()
        if self.allow_binary_archive and self.binary_archive_exists():
            self._install_from_binary_archive()
            source = "binary archives"
        elif self.allow_build:
            self._build_and_install()
            if self.create_binary_archive:
                self._create_binary_archive()
            source = "build"
        else:
            raise UserException(f"Could not find binary archive nor build: {self.build.qualified_name}")
        install_end_time = time.time()

        post_file_list = self._index_directory(tmp_root + orchestra_root, relative_to=tmp_root + orchestra_root)
        post_file_list.append(
            os.path.relpath(installed_component_file_list_path(self.component.name, self.config), orchestra_root)
        )
        post_file_list.append(
            os.path.relpath(installed_component_metadata_path(self.component.name, self.config), orchestra_root)
        )
        new_files = [f for f in post_file_list if f not in pre_file_list]

        if not self.no_merge:
            if is_installed(self.config, self.build.component.name):
                logger.debug("Uninstalling previously installed build")
                uninstall(self.build.component.name, self.config)

            logger.debug("Checking for file conflicts")
            conflicts_list = self._get_conflicts(new_files, orchestra_root)
            if len(conflicts_list) > 0:
                list_joined = "\n".join(conflicts_list)
                raise UserException(f"File conflicts detected:\n{list_joined}\nAborting merge")

            logger.debug("Merging installed files into orchestra root directory")
            self._merge()

            self._update_metadata(
                new_files,
                install_end_time - install_start_time,
                source,
                explicitly_requested,
            )

        if not self.keep_tmproot:
            logger.debug("Cleaning up tmproot")
            self._cleanup_tmproot()

        if self.discard_build_directories:
            logger.debug("Discarding build directory")
            self._discard_build_directory()

    def _update_metadata(self, file_list, install_time, source, set_manually_insalled):
        # Save installed file list (.idx)
        save_file_list(self.component.name, file_list, self.config)

        # Save metadata
        metadata = load_metadata(self.component.name, self.config)
        if metadata is None:
            metadata = init_metadata_from_build(self.build)

        metadata.recursive_hash = self.component.recursive_hash
        metadata.source = source
        metadata.manually_installed = metadata.manually_installed or set_manually_insalled
        metadata.install_time = install_time
        metadata.binary_archive_path = self.binary_archive_relative_path

        save_metadata(metadata, self.config)

    def _prepare_tmproot(self):
        script = dedent(
            """
            rm -rf "$TMP_ROOT"
            mkdir -p "$TMP_ROOT"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/include"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/lib64"{,/include,/pkgconfig}
            test -e "${TMP_ROOT}${ORCHESTRA_ROOT}/lib" || ln -s lib64 "${TMP_ROOT}${ORCHESTRA_ROOT}/lib"
            test -L "${TMP_ROOT}${ORCHESTRA_ROOT}/lib"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/bin"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/usr/"{lib,include}
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/share/"{info,doc,man,orchestra}
            touch "${TMP_ROOT}${ORCHESTRA_ROOT}/share/info/dir"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/libexec"
            """
        )
        self._run_internal_script(script)

    def _install_from_binary_archive(self):
        # TODO: handle nonexisting binary archives
        logger.debug("Fetching binary archive")
        self._fetch_binary_archive()
        logger.debug("Extracting binary archive")
        self._extract_binary_archive()

        logger.debug("Removing conflicting files")
        self._remove_conflicting_files()

    def _fetch_binary_archive(self):
        binary_archive_path = self.locate_binary_archive()
        assert binary_archive_path is not None
        binary_archive_path = pathlib.Path(binary_archive_path)
        binary_archive_root = get_worktree_root(binary_archive_path)
        binary_archive_relative_path = binary_archive_path.relative_to(binary_archive_root)
        failures = 0
        retry_timeout = 5
        while True:
            try:
                lfs.fetch(binary_archive_root, include=[binary_archive_relative_path])
                break
            except InternalSubprocessException as e:
                time.sleep(retry_timeout)
                retry_timeout *= 2
                failures += 1
                if failures >= self.config.max_lfs_retries:
                    raise e

    def _extract_binary_archive(self):
        if not self.binary_archive_exists():
            raise UserException("Binary archive not found!")

        archive_filepath = self.locate_binary_archive()
        script = dedent(
            f"""
            mkdir -p "$TMP_ROOT$ORCHESTRA_ROOT"
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            tar xaf "{archive_filepath}"
            """
        )
        self._run_internal_script(script)

    def _implicit_dependencies(self):
        if self.allow_binary_archive and self.binary_archive_exists() or not self.allow_build:
            return set()
        else:
            return {self.build.configure}

    def _implicit_dependencies_for_hash(self):
        return {self.build.configure}

    def _build_and_install(self):
        env = self.environment
        env["RUN_TESTS"] = "1" if self.run_tests else "0"

        logger.debug("Executing install script")
        run_user_script(self.script, environment=env)

        logger.debug("Removing conflicting files")
        self._remove_conflicting_files()

        if self.build.component.skip_post_install:
            logger.debug("Skipping post install")
        else:
            self._post_install()

    def _post_install(self):
        logger.debug("Collecting tmproot files timestamps")
        tmproot_timestamps = self._collect_times()

        logger.debug("Dropping absolute paths from pkg-config")
        self._drop_absolute_pkgconfig_paths()

        logger.debug("Fix shebangs in bin/")
        self._fix_shebangs()

        logger.debug("Purging libtools' files")
        self._purge_libtools_files()

        # TODO: maybe this should be put into the configuration and not in orchestra itself
        logger.debug("Converting hardlinks to symbolic")
        self._hard_to_symbolic()

        # TODO: maybe this should be put into the configuration and not in orchestra itself
        logger.debug("Fixing RPATHs")
        self._fix_rpath()

        # TODO: this should be put into the configuration and not in orchestra itself
        logger.debug("Replacing NDEBUG preprocessor statements")
        self._replace_ndebug(self.build.ndebug)

        # TODO: this should be put into the configuration and not in orchestra itself
        logger.debug("Replacing ASAN preprocessor statements")
        self._replace_asan(self.build.asan)

        logger.debug("Restoring tmproot files timestamps")
        self._restore_mtimes(tmproot_timestamps)

        if self.build.component.license:
            logger.debug("Copying license file")
            source = self.build.component.license
            destination = installed_component_license_path(self.build.component.name, self.config)
            script = dedent(
                f"""
                DESTINATION_DIR="$TMP_ROOT$(dirname "{destination}")"
                mkdir -p "$DESTINATION_DIR"
                for DIR in "$BUILD_DIR" "${{SOURCE_DIR-/non-existing}}"; do
                  if test -e "$DIR/{source}"; then
                    cp "$DIR/{source}" "$TMP_ROOT/{destination}"
                    exit 0
                  fi
                done
                echo "Couldn't find {source}"
                exit 1
                """
            )
            self._run_internal_script(script)

    def _remove_conflicting_files(self):
        script = dedent(
            """
            if test -d "$TMP_ROOT/$ORCHESTRA_ROOT/share/info"; then
                rm -rf "$TMP_ROOT/$ORCHESTRA_ROOT/share/info";
            fi
            if test -d "$TMP_ROOT/$ORCHESTRA_ROOT/share/locale"; then
                rm -rf "$TMP_ROOT/$ORCHESTRA_ROOT/share/locale";
            fi
            """
        )
        self._run_internal_script(script)

    def _collect_times(self):
        """Returns a dict[path, times], where times is a tuple(atime_ns, mtime_ns)"""
        times = {}
        for root, dirnames, filenames in os.walk(f'{self.environment["TMP_ROOT"]}{self.environment["ORCHESTRA_ROOT"]}'):
            for path in filenames:
                fullpath = os.path.join(root, path)
                info = os.lstat(fullpath)
                times[fullpath] = (info.st_atime_ns, info.st_mtime_ns)
        return times

    @staticmethod
    def _restore_mtimes(mtimes):
        for path, times in mtimes.items():
            if os.path.exists(path):
                os.utime(path, times=None, ns=times)

    def _drop_absolute_pkgconfig_paths(self):
        script = dedent(
            r"""
            cd "${TMP_ROOT}${ORCHESTRA_ROOT}"
            for PKG_PATH in lib/pkgconfig share/pkgconfig; do
              if [ -e "$PKG_PATH" ]; then
                find "$PKG_PATH" -name '*.pc' -print0 | \
                  xargs -0 -r -n 100 -P$(nproc) \
                  sed \
                    -i \
                    's|/*'"$ORCHESTRA_ROOT"'/*|${pcfiledir}/../..|g'
              fi
            done
            """
        )
        self._run_internal_script(script)

    def _fix_shebangs(self):
        script = dedent(
            r"""
            cd "${TMP_ROOT}${ORCHESTRA_ROOT}"
            if [ -e bin ]; then
              find bin -maxdepth 1 -type f -print0 | \
                xargs -0 -r -n 100 -P$(nproc) \
                sed \
                  -i \
                  '1 s|^#!'"$ORCHESTRA_ROOT"'/bin/|#!/usr/bin/env |g'
            fi
            """
        )
        self._run_internal_script(script)

    def _purge_libtools_files(self):
        script = dedent(
            """
            find "${TMP_ROOT}${ORCHESTRA_ROOT}" -name "*.la" -type f -delete
            """
        )
        self._run_internal_script(script)

    def _hard_to_symbolic(self):
        duplicates = defaultdict(list)
        for root, dirnames, filenames in os.walk(f'{self.environment["TMP_ROOT"]}{self.environment["ORCHESTRA_ROOT"]}'):
            for path in filenames:
                path = os.path.join(root, path)
                info = os.lstat(path)
                inode = info.st_ino
                if inode == 0 or info.st_nlink < 2 or not stat.S_ISREG(info.st_mode):
                    continue

                duplicates[inode].append(path)

        for _, equivalent in duplicates.items():
            base = equivalent.pop()
            for alternative in equivalent:
                os.unlink(alternative)
                os.symlink(os.path.relpath(base, os.path.dirname(alternative)), alternative)

    def _fix_rpath(self):
        replace_dynstr = os.path.join(os.path.dirname(__file__), "..", "support", "elf-replace-dynstr.py")
        self._run_internal_script(
            f'"{replace_dynstr}" "$TMP_ROOT$ORCHESTRA_ROOT" "$RPATH_PLACEHOLDER" "$ORCHESTRA_ROOT"'
        )

    def _replace_ndebug(self, disable_debugging):
        debug, ndebug = ("0", "1") if disable_debugging else ("1", "0")
        patch_ndebug_script = dedent(
            rf"""
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            find include/ -name '*.h' -print0 | \
              xargs -0 -r -n 100 -P$(nproc) \
              sed -i \
                -e 's|^\s*#\s*ifndef\s\+NDEBUG|#if {debug}|' \
                -e 's|^\s*#\s*ifdef\s\+NDEBUG|#if {ndebug}|' \
                -e 's|^\(\s*#\s*if\s\+.*\)!defined(NDEBUG)|\1{debug}|' \
                -e 's|^\(\s*#\s*if\s\+.*\)defined(NDEBUG)|\1{ndebug}|'
            """
        )
        self._run_internal_script(patch_ndebug_script)

    def _replace_asan(self, asan_enabled):
        replace_with = "1" if asan_enabled else "0"
        # fmt: off
        patch_ndebug_script = dedent(rf"""
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            find include/ -name '*.h' -print0 | \
              xargs -0 -r -n 100 -P$(nproc) \
              sed -i \
                -e 's|__has_feature\(address_sanitizer\)|{replace_with}|' \
                -e 's|defined\(__SANITIZE_ADDRESS__\)|{replace_with}|'
            """)
        # fmt: on
        self._run_internal_script(patch_ndebug_script)

    def _get_conflicts(self, file_list: Iterable[str], root: str) -> List[str]:
        return [file for file in file_list if os.path.exists(os.path.join(root, file))]

    def _merge(self):
        copy_command = 'cp -ar --reflink=auto "$TMP_ROOT/$ORCHESTRA_ROOT/." "$ORCHESTRA_ROOT"'
        self._run_internal_script(copy_command)

    def _create_binary_archive(self):
        if self.binary_archive_exists():
            logger.debug(f"Binary archive for {self.component.name} already exists, skipping its creation")
            return
        logger.debug("Creating binary archive")
        binary_archive_path = self._binary_archive_path()
        binary_archive_parent_dir = os.path.dirname(binary_archive_path)
        binary_archive_repo_name = self._binary_archive_repo_name
        absolute_binary_archive_tmp_path = os.path.join(
            self.config.binary_archives_local_paths[binary_archive_repo_name],
            f"_tmp_{self.binary_archive_filename}",
        )
        script = dedent(
            f"""
            mkdir -p "$BINARY_ARCHIVES"
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            rm -f '{absolute_binary_archive_tmp_path}'
            export XZ_OPT='-T0'
            tar cvaf '{absolute_binary_archive_tmp_path}' --owner=0 --group=0 *
            mkdir -p '{binary_archive_parent_dir}'
            mv '{absolute_binary_archive_tmp_path}' '{binary_archive_path}'
            """
        )
        self._run_internal_script(script)
        self._save_hash_material()

    def _save_hash_material(self):
        logger.debug("Saving hash material")
        hash_material_path = Path(self._hash_material_path())
        hash_material_path.write_text(self.component.recursive_hash_material())

    def symlink_binary_archive(self, name: str):
        """Creates/updates convenience symlinks to the binary archive with the specified name.
        Example: {name}.tar.xz -> abcdef_fedcba.tar.xz would be created if `abcdef_defcba.tar.xz`
        exists in the binary archives.
        """
        logger.debug("Adding binary archive symlink")

        if self._binary_archive_repo_name is None:
            logger.warning("No binary archive configured")
            return

        if self.component.clone:
            _, commit = self.component.clone.branch()
        else:
            commit = "none"

        archive_dir_path = os.path.dirname(self._binary_archive_path())
        target_name = self._binary_archive_filename(commit, self.component.recursive_hash)
        target_absolute_path = os.path.join(archive_dir_path, target_name)
        symlink_absolute_path = os.path.join(archive_dir_path, f"{name}.tar.xz")
        if os.path.exists(target_absolute_path):
            if os.path.exists(symlink_absolute_path):
                os.unlink(symlink_absolute_path)
            os.symlink(target_name, symlink_absolute_path)

    @staticmethod
    def _index_directory(root_dir_path, relative_to=None):
        paths = []
        for current_dir_path, child_dir_names, child_file_names in os.walk(root_dir_path):
            for child_filename in child_file_names:
                child_file_path = os.path.join(current_dir_path, child_filename)
                if relative_to:
                    child_file_path = os.path.relpath(child_file_path, relative_to)
                paths.append(child_file_path)

            for child_dir in child_dir_names:
                child_dir_path = os.path.join(current_dir_path, child_dir)
                if os.path.islink(child_dir_path):
                    if relative_to:
                        child_dir_path = os.path.relpath(child_dir_path, relative_to)
                    paths.append(child_dir_path)

        return paths

    def _cleanup_tmproot(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _discard_build_directory(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)

    @property
    def _binary_archive_repo_name(self):
        """Returns the name of the binary archives repository where new archives should be created"""
        if self.component.binary_archives:
            binary_archive_repo_name = self.component.binary_archives
            if binary_archive_repo_name not in self.config.binary_archives_remotes.keys():
                raise UserException(
                    f"Component {self.component.name} wants to push to an unknown binary-archives "
                    f"repository ({binary_archive_repo_name})"
                )
            return binary_archive_repo_name
        elif self.config.binary_archives_remotes:
            return list(self.config.binary_archives_remotes.keys())[0]
        else:
            return None

    @property
    def binary_archive_relative_path(self) -> str:
        """Returns the path to the binary archive, relative to the binary archive repository"""
        return os.path.join(
            self.binary_archive_relative_dir,
            self.binary_archive_filename,
        )

    @property
    def hash_material_relative_path(self) -> str:
        """Returns the path to the hash material, relative to the binary archive repository"""
        return os.path.join(
            self.binary_archive_relative_dir,
            self.hash_material_filename,
        )

    @property
    def binary_archive_filename(self) -> str:
        """Returns the filename of the binary archive for the target build.
        *Warning*: the filename is the same for all the builds of the same component. Use `binary_archive_relative_path`
        to get a path which is unique to a single build
        """
        component_commit = self.component.commit() or "none"
        return self._binary_archive_filename(component_commit, self.component.recursive_hash)

    @property
    def binary_archive_relative_dir(self) -> str:
        """Returns the path to the directory containing the binary archives for the associated build, relative to the
        binary archive repository"""
        return os.path.join(
            self.architecture,
            self.component.name,
            self.build.name,
        )

    @property
    def hash_material_filename(self) -> str:
        """Returns the filename of the hash material for the target build.
        *Warning*: the filename is the same for all the builds of the same component. Use `hash_material_relative_path`
        to get a path which is unique to a single build
        """
        component_commit = self.component.commit() or "none"
        return self._hash_material_filename(component_commit, self.component.recursive_hash)

    @staticmethod
    def _binary_archive_filename(component_commit, component_recursive_hash) -> str:
        return f"{component_commit}_{component_recursive_hash}.tar.xz"

    @staticmethod
    def _hash_material_filename(component_commit, component_recursive_hash) -> str:
        return f"{component_commit}_{component_recursive_hash}.hash-material.yml"

    def _binary_archive_path(self) -> str:
        """Returns the absolute path where the binary archive should be created.
        Note: Use `locate_binary_archive` to locate the binary archive to extract when installing.
        """
        return os.path.join(
            self.config.binary_archives_local_paths[self._binary_archive_repo_name],
            self.binary_archive_relative_path,
        )

    def available_binary_archives(self):
        """Returns all available binary archives related to this build"""
        available_binary_archives = set()
        for binary_archive_repo in self.config.binary_archives_local_paths.values():
            binary_archives_glob = os.path.join(
                binary_archive_repo, f"{self.build.install.binary_archive_relative_dir}/*.tar.*"
            )
            for binary_archive in glob.glob(binary_archives_glob):
                binary_archive_path = Path(binary_archive)
                if not binary_archive_path.exists() or binary_archive_path.is_symlink():
                    continue
                available_binary_archives.add(binary_archive)
        return available_binary_archives

    def _hash_material_path(self) -> str:
        """Returns the absolute path where the material used to compute the component hash should be created"""
        return os.path.join(
            self.config.binary_archives_local_paths[self._binary_archive_repo_name],
            self.hash_material_relative_path,
        )

    def locate_binary_archive(self) -> Optional[str]:
        """Returns the absolute path to the binary archive that can be extracted to install the target build.
        *Note*: the path may be pointing to a git LFS pointer which needs to be downloaded and checked out (smudged)"""
        binary_archives_path = self.config.binary_archives_dir
        for name in self.config.binary_archives_remotes:
            relative_path_without_extension = os.path.splitext(self.binary_archive_relative_path)[0]
            extensions = [".xz", ".gz", ""]
            for extension in extensions:
                try_path = os.path.join(binary_archives_path, name, relative_path_without_extension + extension)
                if os.path.exists(try_path):
                    return try_path
        return None

    def binary_archive_exists(self) -> bool:
        """Returns True if the binary archive for the target build exists (cached or downloadable)"""
        return self.locate_binary_archive() is not None

    @property
    def environment(self) -> "OrderedDict[str, str]":
        env = super().environment
        env["DESTDIR"] = self.tmp_root
        return env

    @property
    def architecture(self):
        return "linux-x86-64"

    def is_satisfied(self):
        return is_installed(
            self.config,
            self.build.component.name,
            wanted_build=self.build.name,
            wanted_recursive_hash=self.build.component.recursive_hash,
        )

    def assert_prerequisites_are_met(self):
        super().assert_prerequisites_are_met()
        # Verify either sources or ls-remote info are available
        if self.component.clone is not None and self.component.commit() is None:
            raise UserException(f"HEAD commit for {self.component.name} not available. Run `orc update`.")

        # Verify binary archive is available
        if not self.allow_build and not self.binary_archive_exists():
            raise BinaryArchiveNotFoundException(self)

        # Check that if binary archives creation is requested we have a binary archive repo where it will be saved
        if self.create_binary_archive and self._binary_archive_repo_name is None:
            raise UserException("Cannot create binary archive, no binary archives are configured")
