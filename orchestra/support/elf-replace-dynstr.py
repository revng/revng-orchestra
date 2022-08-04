#!/usr/bin/env python3

import argparse
import os
import sys

from elftools.elf.dynamic import DynamicSegment
from elftools.elf.elffile import ELFFile


def log_error(msg):
    sys.stderr.write("[ERROR] {}\n".format(msg))


def log(msg):
    sys.stderr.write(msg + "\n")


def unique_or_none(list):
    if not list:
        return None
    assert len(list) == 1
    return list[0]


def fix_elf_file(elf_file, path, root_path, search_strings):
    elf = ELFFile(elf_file)
    dynamic = unique_or_none([segment for segment in elf.iter_segments() if type(segment) is DynamicSegment])

    if dynamic is None:
        log("Not a dynamic executable")
        return 0

    address = unique_or_none([tag.entry.d_val for tag in dynamic.iter_tags() if tag.entry.d_tag == "DT_STRTAB"])

    offset = None
    if address:
        offset = unique_or_none(list(elf.address_offsets(address)))

    size = unique_or_none([tag.entry.d_val for tag in dynamic.iter_tags() if tag.entry.d_tag == "DT_STRSZ"])

    if offset is None or size is None:
        log("DT_STRTAB not found")
        return 0

    elf_file.seek(offset)
    original = elf_file.read(size)

    fail = False
    new = original
    for search_string in search_strings:
        replace = b"$ORIGIN/"
        replace += os.path.relpath(root_path, os.path.dirname(path))

        if len(replace) > len(search_string):
            log("The search string is shorter than replace:")
            log("  " + search_string.decode("ascii"))
            log("  " + replace.decode("ascii"))

        if len(replace) < len(search_string):
            replace = replace + b"/" * (len(search_string) - len(replace))
            assert len(replace) == len(search_string)

        new = new.replace(search_string, replace)

    if new != original:
        if fail:
            log("Search string is shorter than replacement.")
            return 1
        log(f"""Patching {path.decode("ascii")}""")
        elf_file.seek(offset)
        elf_file.write(new)

    return 0


def main():
    parser = argparse.ArgumentParser(description="Rewrite portions of .dynstr.")
    parser.add_argument("path", metavar="PATH", help="path to search in.")
    parser.add_argument("search_strings", metavar="SEARCH_STRINGS", nargs="+", help="strings to search.")
    args = parser.parse_args()

    search_strings = [search_string.encode("ascii") for search_string in args.search_strings]

    for directory, _, files in os.walk(args.path):
        for file_name in files:
            path = os.path.join(directory, file_name)

            if not os.path.isfile(path) or os.path.islink(path):
                continue

            if not os.access(path, os.X_OK):
                continue

            with open(path, "rb+") as elf_file:
                if elf_file.read(4) != b"\x7fELF":
                    continue
                elf_file.seek(0)

                result = fix_elf_file(elf_file, path.encode("ascii"), args.path.encode("ascii"), search_strings)

                if result != 0:
                    return result

    return 0


if __name__ == "__main__":
    sys.exit(main())
