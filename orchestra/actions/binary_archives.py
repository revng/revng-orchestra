import os
from textwrap import dedent

from .action import Action
from .util import run_script
from ..util import is_installed


class CreateBinaryArchivesActionAction(Action):
    def _create_binary_archive(self):
        archive_name = self._binary_archive_filename()
        script = dedent(f"""
            mkdir -p "$BINARY_ARCHIVES"
            cd "$TMP_ROOT$ORCHESTRA_ROOT"
            tar caf "$BINARY_ARCHIVES/{archive_name}" --owner=0 --group=0 "."
        """)
        run_script(script, show_output=True, environment=self.environment)


class InstallFromBinaryArchives(Action):
    def __init__(self, build, config):
        super().__init__("install from binary archive", build, "", config)

    def _run(self, show_output=False, args=None):
        if not self._binary_archive_present():
            raise Exception(f"Binary archive for {self.build.qualified_name} not found")

        # TODO: fetch binary archive

        archives_dir = self.environment["BINARY_ARCHIVES"]
        archive_name = self._binary_archive_filename()
        archive_filepath = os.path.join(archives_dir, archive_name)
        script = dedent(f"""
                    mkdir -p "$TMP_ROOT$ORCHESTRA_ROOT"
                    cd "$TMP_ROOT$ORCHESTRA_ROOT"
                    tar xaf "{archive_filepath}"
                    """)
        run_script(script, environment=self.environment)

    def _is_satisfied(self):
        return is_installed(self.config, self.build.component.name, wanted_build=self.build.name)

    def _binary_archive_present(self):
        archives_dir = self.environment["BINARY_ARCHIVES"]
        archive_name = self._binary_archive_filename()
        archive_filepath = os.path.join(archives_dir, archive_name)
        return os.path.exists(archive_filepath)

    def _binary_archive_filename(self):
        config_hash = self.config.config_hash
        safe_build_name = self.build.qualified_name.replace("@", "_").replace("/", "_")
        return f'{safe_build_name}_{config_hash}.tar.gz'
