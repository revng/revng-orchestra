#!/usr/bin/env python3

import os.path
import urllib.request
from setuptools import setup, find_packages

ytt_url = "https://github.com/k14s/ytt/releases/download/v0.30.0/ytt-linux-amd64"
ytt_path = os.path.join(os.path.dirname(__file__), "orchestra/support/ytt")
if not os.path.exists(ytt_path):
    print(f"ytt not found, downloading from {ytt_url}")
    with urllib.request.urlopen(ytt_url) as ytt_download:
        with open(ytt_path, "wb") as out:
            out.write(ytt_download.read())
    os.chmod(ytt_path, 0o755)

setup(
    name='orchestra',
    version='3.0',
    description='The Orchestra meta build system',
    author='Filippo Cremonese (rev.ng SRLs)',
    author_email='filippocremonese@rev.ng',
    # TODO
    url='https://rev.ng/gitlab/',
    packages=find_packages(),
    package_data={"orchestra": ["support/*"]},
    install_requires=open("requirements.txt").readlines(),
    entry_points={
        "console_scripts": [
            "orchestra=orchestra:main",
        ]
    },
    zip_safe=False,
)

