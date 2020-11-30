import json
import os
import stat
import time
from collections import OrderedDict, defaultdict
from textwrap import dedent

from loguru import logger

from .action import ActionForBuild
from .uninstall import uninstall
from .util import run_script, OrchestraException
from .. import git_lfs
from ..util import is_installed


class InstallAction(ActionForBuild):
    def __init__(self, build, script, config, allow_build=True, allow_binary_archive=True, run_tests=False):
        if not allow_build and not allow_binary_archive:
            raise Exception(f"You must allow at least one option between "
                            f"building and installing from binary archives for {build.name}")
        sources = []
        if allow_build:
            sources.append("build")
        if allow_binary_archive:
            sources.append("binary archives")
        sources_str = " or ".join(sources)

        super().__init__(f"install ({sources_str})", build, script, config)
        self.allow_build = allow_build
        self.allow_binary_archive = allow_binary_archive

    def _run(self, args):
        tmp_root = self.environment["TMP_ROOT"]
        orchestra_root = self.environment['ORCHESTRA_ROOT']

        logger.info("Preparing temporary root directory")
        self._prepare_tmproot()

        pre_file_list = self._index_directory(tmp_root + orchestra_root, relative_to=tmp_root + orchestra_root)

        install_start_time = time.time()
        if self.allow_binary_archive and self._binary_archive_exists():
            self._install_from_binary_archive(args)
            source = "binary archives"
        elif self.allow_build:
            self._build_and_install(args)
            if getattr(args, "create_binary_archives", False):
                self._create_binary_archive()
                self.update_binary_archive_symlink()
            source = "build"
        else:
            raise OrchestraException(f"Could not find binary archive nor build: {self.build.qualified_name}")
        install_end_time = time.time()

        post_file_list = self._index_directory(tmp_root + orchestra_root, relative_to=tmp_root + orchestra_root)
        post_file_list.append(
            os.path.relpath(self.config.installed_component_file_list_path(self.build.component.name), orchestra_root))
        post_file_list.append(
            os.path.relpath(self.config.installed_component_metadata_path(self.build.component.name), orchestra_root))
        new_files = [f for f in post_file_list if f not in pre_file_list]

        if not args.no_merge:
            if is_installed(self.config, self.build.component.name):
                logger.info("Uninstalling previously installed build")
                uninstall(self.build.component.name, self.config)

            logger.info("Merging installed files into orchestra root directory")
            self._merge(args.quiet)

            # Write file metadata and index
            os.makedirs(self.config.installed_component_metadata_dir(), exist_ok=True)
            metadata = {
                "component_name": self.build.component.name,
                "build_name": self.build.name,
                "install_time": install_end_time - install_start_time,
                "source": source,
                "self_hash": self.build.component.self_hash,
                "recursive_hash": self.build.component.recursive_hash,
                "binary_archive_path": os.path.join(self.build.binary_archive_dir, self.build.binary_archive_filename),
            }
            with open(self.config.installed_component_metadata_path(self.build.component.name), "w") as f:
                json.dump(metadata, f)

            with open(self.config.installed_component_file_list_path(self.build.component.name), "w") as f:
                new_files = [f"{f}\n" for f in new_files]
                f.writelines(new_files)

        if not args.keep_tmproot:
            logger.info("Cleaning up tmproot")
            self._cleanup_tmproot()

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
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/share/"{info,doc,man,orchestra}
            touch "${TMP_ROOT}${ORCHESTRA_ROOT}/share/info/dir"
            mkdir -p "${TMP_ROOT}${ORCHESTRA_ROOT}/libexec"
            """)
        run_script(script, environment=self.environment)

    def _install_from_binary_archive(self, args):
        # TODO: handle nonexisting binary archives
        logger.info("Fetching binary archive")
        self._fetch_binary_archive()
        logger.info("Extracting binary archive")
        self._extract_binary_archive()

        logger.info("Removing conflicting files")
        self._remove_conflicting_files()

    def _fetch_binary_archive(self):
        # TODO: better edge-case handling, when the binary archive exists but is not committed into the
        #   binary archives git-lfs repo (e.g. it has been locally created by the user)
        binary_archive_path = self._binary_archive_filepath()
        binary_archive_repo_dir = os.path.dirname(binary_archive_path)
        while binary_archive_repo_dir != "/":
            if ".git" in os.listdir(binary_archive_repo_dir):
                break
            binary_archive_repo_dir = os.path.dirname(binary_archive_repo_dir)
        if binary_archive_repo_dir == "/":
            logger.error("Binary archives are not a git repository!")
            exit(1)
        git_lfs.fetch(binary_archive_repo_dir, only=[os.path.realpath(binary_archive_path)])

    def _extract_binary_archive(self):
        if not self._binary_archive_exists():
            raise Exception("Binary archive not found!")

        archive_filepath = self._binary_archive_filepath()
        script = dedent(f"""
            mkdir -p "$TMP_ROOT$ORCHESTRA_ROOT"
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            tar xaf "{archive_filepath}"
            """)
        run_script(script, environment=self.environment, quiet=True)

    def _implicit_dependencies(self):
        if self.allow_binary_archive and self._binary_archive_exists():
            return set()
        else:
            return {self.build.configure}

    def _build_and_install(self, args):
        logger.info("Executing install script")
        run_script(self.script, quiet=args.quiet, environment=self.environment)

        logger.info("Removing conflicting files")
        self._remove_conflicting_files()

        if self.build.component.skip_post_install:
            logger.info("Skipping post install")
        else:
            self._post_install(args.quiet)

    def _post_install(self, quiet):
        logger.info("Dropping absolute paths from pkg-config")
        self._drop_absolute_pkgconfig_paths()

        logger.info("Purging libtools' files")
        self._purge_libtools_files()

        # TODO: maybe this should be put into the configuration and not in orchestra itself
        logger.info("Converting hardlinks to symbolic")
        self._hard_to_symbolic()

        # TODO: maybe this should be put into the configuration and not in orchestra itself
        logger.info("Fixing RPATHs")
        self._fix_rpath()

        # TODO: this should be put into the configuration and not in orchestra itself
        logger.info("Replacing NDEBUG preprocessor statements")
        self._replace_ndebug(self.build.ndebug)

        if self.build.component.license:
            logger.info("Copying license file")
            source = self.build.component.license
            destination = self.config.installed_component_license_path(self.build.component.name)
            script = dedent(f"""
                DESTINATION_DIR="$(dirname "{destination}")"
                mkdir -p "$DESTINATION_DIR"
                for DIR in "$BUILD_DIR" "$SOURCE_DIR"; do
                  if test -e "$DIR/{source}"; then
                    cp "$DIR/{source}" "$TMP_ROOT/{destination}"
                    exit 0
                  fi
                done
                echo "Couldn't find {source}"
                exit 1
                """)
            run_script(script, environment=self.environment)

    def _remove_conflicting_files(self):
        script = dedent("""
            if test -d "$TMP_ROOT/$ORCHESTRA_ROOT/share/info"; then rm -rf "$TMP_ROOT/$ORCHESTRA_ROOT/share/info"; fi
            if test -d "$TMP_ROOT/$ORCHESTRA_ROOT/share/locale"; then rm -rf "$TMP_ROOT/$ORCHESTRA_ROOT/share/locale"; fi
            """)
        run_script(script, environment=self.environment)

    def _drop_absolute_pkgconfig_paths(self):
        script = dedent("""
            cd "${TMP_ROOT}${ORCHESTRA_ROOT}"
            if [ -e lib/pkgconfig ]; then
                find lib/pkgconfig \\
                    -name "*.pc" \\
                    -exec sed -i 's|/*'"$ORCHESTRA_ROOT"'/*|${pcfiledir}/../..|g' {} ';'
            fi
            """)
        run_script(script, environment=self.environment)

    def _purge_libtools_files(self):
        script = dedent("""
            find "${TMP_ROOT}${ORCHESTRA_ROOT}" -name "*.la" -type f -delete
            """)
        run_script(script, environment=self.environment)

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
        fix_rpath_script = dedent(f"""
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            # Fix rpath
            find . -type f -executable | while read EXECUTABLE; do
                if head -c 4 "$EXECUTABLE" | grep '^.ELF' > /dev/null &&
                        file "$EXECUTABLE" | grep x86-64 | grep -E '(shared|dynamic)' > /dev/null;
                then
                    REPLACE='$'ORIGIN/$(realpath --relative-to="$(dirname "$EXECUTABLE")" ".")
                    echo "Setting rpath of $EXECUTABLE to $REPLACE"
                    "{replace_dynstr}" "$EXECUTABLE" "$RPATH_PLACEHOLDER" "$REPLACE" /
                    "{replace_dynstr}" "$EXECUTABLE" "$ORCHESTRA_ROOT" "$REPLACE" /
                fi
            done
            """)
        run_script(fix_rpath_script, environment=self.environment)

    def _replace_ndebug(self, disable_debugging):
        debug, ndebug = ("0", "1") if disable_debugging else ("1", "0")
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
        run_script(patch_ndebug_script, environment=self.environment)

    def _merge(self, quiet):
        copy_command = f'cp -farl "$TMP_ROOT/$ORCHESTRA_ROOT/." "$ORCHESTRA_ROOT"'
        run_script(copy_command, quiet=quiet, environment=self.environment)

    def _binary_archive_repo_name(self):
        # Select the binary archives repository to employ
        if self.component.binary_archives:
            binary_archive_repo_name = self.component.binary_archives
            if binary_archive_repo_name not in self.config.binary_archives_remotes.keys():
                raise Exception(f"The {self.component.name} component wants to "
                                f"push to an unknown binary-archives repository ({binary_archive_repo_name})")
        else:
            return list(self.config.binary_archives_remotes.keys())[0]

    def _binary_archive_path(self):
        archive_dirname = self.build.binary_archive_dir
        archive_name = self.build.binary_archive_filename
        binary_archive_repo_name = self._binary_archive_repo_name()
        return f"$BINARY_ARCHIVES/{binary_archive_repo_name}/linux-x86-64/{archive_dirname}/{archive_name}"

    def _create_binary_archive(self):
        logger.info("Creating binary archive")
        archive_name = self.build.binary_archive_filename
        binary_archive_path = self._binary_archive_path()
        binary_archive_repo_name = self._binary_archive_repo_name()
        binary_archive_tmp_path = f"$BINARY_ARCHIVES/{binary_archive_repo_name}/_tmp_{archive_name}"
        binary_archive_containing_dir = os.path.dirname(binary_archive_path)
        script = dedent(f"""
            mkdir -p "$BINARY_ARCHIVES"
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            rm -f "{binary_archive_tmp_path}"
            tar cvaf "{binary_archive_tmp_path}" --owner=0 --group=0 *
            mkdir -p "{binary_archive_containing_dir}"
            mv "{binary_archive_tmp_path}" "{binary_archive_path}"
            """)
        run_script(script, environment=self.environment)

    def update_binary_archive_symlink(self):
        logger.info("Updating binary archive symlink")

        binary_archive_repo_name = self._binary_archive_repo_name()
        archive_dirname = self.build.binary_archive_dir

        orchestra_config_branch = run_script(
            'git -C "$ORCHESTRA_DOTDIR" rev-parse --abbrev-ref HEAD',
            quiet=True,
            environment=self.environment
        ).stdout.decode("utf-8").strip().replace("/", "-")

        archive_path = os.path.join(self.environment["BINARY_ARCHIVES"],
                                    binary_archive_repo_name,
                                    "linux-x86-64",
                                    archive_dirname)

        def create_symlink(branch, commit):
            branch = branch.replace("/", "-")
            target_name = f"{commit}_{self.build.component.recursive_hash}.tar.gz"
            target = os.path.join(archive_path, target_name)
            if os.path.exists(target):
                symlink = os.path.join(archive_path, f"{branch}_{orchestra_config_branch}.tar.gz")
                if os.path.exists(symlink):
                    os.unlink(symlink)
                os.symlink(target_name, symlink)

        if self.component.clone:
            for branch, commit in self.component.clone.branches().items():
                create_symlink(branch, commit)
        else:
            create_symlink("none", "none")

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
        run_script('rm -rf "$TMP_ROOT"', environment=self.environment, quiet=True)

    def _binary_archive_filepath(self):
        archives_dir = self.environment["BINARY_ARCHIVES"]
        for name in self.config.binary_archives_remotes:
            archive_dir = self.build.binary_archive_dir
            archive_name = self.build.binary_archive_filename
            try_archive_path = os.path.join(archives_dir, name, "linux-x86-64", archive_dir, archive_name)
            if os.path.exists(try_archive_path):
                return try_archive_path
        return None

    def _binary_archive_exists(self):
        return self._binary_archive_filepath() is not None

    @property
    def environment(self) -> OrderedDict:
        env = super().environment
        env["DESTDIR"] = env["TMP_ROOT"]
        return env

    def is_satisfied(self):
        return is_installed(
            self.config,
            self.build.component.name,
            wanted_build=self.build.name,
            wanted_recursive_hash=self.build.component.recursive_hash
        )
