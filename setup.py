#!/usr/bin/env python3

import os.path
import urllib.request
from setuptools import setup, find_packages
import setuptools.command.install_lib

ytt_url = "https://github.com/k14s/ytt/releases/download/v0.30.0/ytt-linux-amd64"
ytt_path = os.path.join(os.path.dirname(__file__), "orchestra/support/ytt")
if not os.path.exists(ytt_path):
    print(f"ytt not found, downloading from {ytt_url}")
    with urllib.request.urlopen(ytt_url) as ytt_download:
        with open(ytt_path, "wb") as out:
            out.write(ytt_download.read())
    os.chmod(ytt_path, 0o755)


def is_an_executable_support_file(path: str):
    return any(path.endswith(f) for f in executable_support_files)


class InstallAndSetExecutableBit(setuptools.command.install_lib.install_lib):
    def run(self):
        setuptools.command.install_lib.install_lib.run(self)
        for filename in self.get_outputs():
            if is_an_executable_support_file(filename):
                mode = (os.stat(filename).st_mode | 0o555) & 0o7777
                print(f"Changing mode of {filename} to {mode:o}")
                os.chmod(filename, mode)


# For unknown reasons, setuptools does not preserve package_data file permissions so we need to set the executable
# flag ourselves
executable_support_files = [
    "support/ytt",
    "support/elf-replace-dynstr.py",
    "support/verify-root",
]

setup(
    name="orchestra",
    version="3.0.0",
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
    cmdclass={"install_lib": InstallAndSetExecutableBit},
)
