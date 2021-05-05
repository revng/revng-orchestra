#!/usr/bin/env python3

from pathlib import Path
import setuptools.command.install_lib
import subprocess
import os.path

from setuptools import setup, find_packages
from typing import List, Callable

version = (Path(__file__).parent / "orchestra/support/VERSION").read_text().strip()
ensure_ytt_path = Path(__file__).parent / "orchestra/support/ensure_ytt.py"

# For unknown reasons, setuptools does not preserve package_data file permissions so we need to set the executable
# flag ourselves
executable_support_files = [
    "support/ytt",
    "support/elf-replace-dynstr.py",
    "support/verify-root",
    "support/ensure_ytt.py",
]


def is_an_executable_support_file(path: str):
    return any(path.endswith(f) for f in executable_support_files)


def set_executable_bit(install_lib_instance: setuptools.command.install_lib.install_lib):
    for filename in install_lib_instance.get_outputs():
        if is_an_executable_support_file(filename):
            mode = (os.stat(filename).st_mode | 0o555) & 0o7777
            print(f"Changing mode of {filename} to {mode:o}")
            os.chmod(filename, mode)


class ExtensibleInstallLibCommandFactory:
    def __init__(
        self,
        additional_actions: List[Callable[[setuptools.command.install_lib.install_lib], None]],
    ):
        """Provides a way to create a class that extends setuptools install_lib commands and executes arbitrary actions
        after it the default one has finished. Each additional action to be performed must be a Callable which takes an
        install_lib instance as argument.
        """
        self.additional_actions: List[Callable[[setuptools.command.install_lib.install_lib], None]] = additional_actions

    def get_command(self):
        additional_actions = self.additional_actions

        class ExtensibleInstallLibCommand(setuptools.command.install_lib.install_lib):
            def run(self):
                setuptools.command.install_lib.install_lib.run(self)
                for action in additional_actions:
                    action(self)

        return ExtensibleInstallLibCommand


custom_install_lib_cmd = ExtensibleInstallLibCommandFactory(
    additional_actions=[
        set_executable_bit,
    ]
).get_command()

subprocess.check_call([ensure_ytt_path])

setup(
    name="orchestra",
    version=version,
    description="The orchestra meta build system",
    author="Filippo Cremonese (rev.ng SRLs)",
    author_email="filippocremonese@rev.ng",
    url="https://github.com/revng/revng-orchestra",
    packages=find_packages(),
    package_data={
        "orchestra": [
            "support/shell-home/.bashrc",
            "support/shell-home/.zshrc",
            "support/config.schema.yml",
            "support/VERSION",
        ]
        + executable_support_files
    },
    install_requires=open("requirements.txt").readlines(),
    entry_points={
        "console_scripts": [
            "orchestra=orchestra:main",
            "orc=orchestra:main",
        ]
    },
    zip_safe=False,
    cmdclass={"install_lib": custom_install_lib_cmd},
)
