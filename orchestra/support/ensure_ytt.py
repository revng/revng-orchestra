#!/usr/bin/env python3

import os
import urllib.request

ytt_url = "https://github.com/k14s/ytt/releases/download/v0.32.0/ytt-linux-amd64"


def ensure_ytt():
    ytt_path = os.path.join(os.path.dirname(__file__), "ytt")
    if not os.path.exists(ytt_path):
        print(f"ytt not found, downloading from {ytt_url}")
        with urllib.request.urlopen(ytt_url) as ytt_download:
            with open(ytt_path, "wb") as out:
                out.write(ytt_download.read())
        os.chmod(ytt_path, 0o755)


if __name__ == "__main__":
    ensure_ytt()
