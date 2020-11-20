#!/usr/bin/env python3

import argparse
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


def main():
    parser = argparse.ArgumentParser(description="Rewrite portions of .dynstr.")
    parser.add_argument("elf_path", metavar="ELF", help="path to the ELF file.")
    parser.add_argument("search", metavar="SEARCH", help="string to search.")
    parser.add_argument("replace", metavar="REPLACE", help="replacement.")
    parser.add_argument("padding", metavar="PADDING", nargs="?", default="\x00", help="padding (default NUL).")
    args = parser.parse_args()

    fail = False
    if len(args.replace) > len(args.search):
        fail = True

    if len(args.replace) < len(args.search):
        args.replace = args.replace + args.padding * (len(args.search) - len(args.replace))

    args.replace = args.replace.encode("ascii")
    args.search = args.search.encode("ascii")

    with open(args.elf_path, "rb+") as elf_file:
        elf = ELFFile(elf_file)
        dynamic = unique_or_none([segment
                                  for segment
                                  in elf.iter_segments()
                                  if type(segment) is DynamicSegment])

        if dynamic is None:
            log("Not a dynamic executable")
            return 0

        address = unique_or_none([tag.entry.d_val
                                  for tag
                                  in dynamic.iter_tags()
                                  if tag.entry.d_tag == "DT_STRTAB"])

        offset = None
        if address:
            offset = unique_or_none(list(elf.address_offsets(address)))

        size = unique_or_none([tag.entry.d_val
                               for tag
                               in dynamic.iter_tags()
                               if tag.entry.d_tag == "DT_STRSZ"])

        if offset is None or size is None:
            log("DT_STRTAB not found")
            return 0

        elf_file.seek(offset)
        original = elf_file.read(size)

        new = original.replace(args.search, args.replace)
        if new != original:
            if fail:
                log("Search string is shorter than replacement.")
                return 1
            log("Patching")
            elf_file.seek(offset)
            elf_file.write(new)
        else:
            log("Nothing to patch")

    return 0


if __name__ == "__main__":
    sys.exit(main())
