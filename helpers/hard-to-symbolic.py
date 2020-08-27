#!/usr/bin/env python3

import argparse
import os
import stat
import sys

from collections import defaultdict


def log_error(msg):
    sys.stderr.write(msg + "\n")


def main():
    parser = argparse.ArgumentParser(description="Convert hard links to symlinks.")
    parser.add_argument("path", metavar="PATH", help="path where hard links should be searched.")
    args = parser.parse_args()

    duplicates = defaultdict(list)
    for root, dirnames, filenames in os.walk(args.path):
        for path in filenames:
            path = os.path.join(root, path)
            info = os.lstat(path)
            inode = info.st_ino
            if (inode == 0
                    or info.st_nlink < 2
                    or stat.S_ISREG(info.st_mode)):
                continue

            duplicates[inode].append(path)

    for _, equivalent in duplicates.items():
        base = equivalent.pop()
        for alternative in equivalent:
            os.unlink(alternative)
            os.symlink(os.path.relpath(base, os.path.dirname(alternative)),
                       alternative)


if __name__ == "__main__":
    sys.exit(main())
