from typing import Set

import subprocess


def compare_tree(actual_value: Set[str], expected_value: Set[str]):
    """Compares two directory trees returned by the `tree` function"""
    return sorted(actual_value) == sorted(expected_value)


def compare_root_tree(root_path: str, expected_tree: Set[str]):
    """Compares the tree of `root_path` with the expected one.
    The expected directory tree does not need to contain directories and files placed by in the root by orchestra by
    default. It does need to include metadata files.
    """
    actual_root_tree = tree(root_path)
    expected_tree = set(expected_tree).union(tree_output_in_empty_root)
    return compare_tree(actual_root_tree, expected_tree)


def tree(dir: str) -> Set[str]:
    """Returns a list representing the directory tree of `dir`."""
    listing = set(
        subprocess.check_output(["tree", "-naifF", "--noreport"], cwd=dir).strip().decode("utf8").splitlines()
    )
    fixed_listing = set()
    for item in listing:
        # tree < 2.0.0 outputs the root of the tree as `.` even with the -F option
        if item == ".":
            item = "./"
        fixed_listing.add(item)
    return fixed_listing


# Output of `tree()` on an empty root directory
tree_output_in_empty_root = {
    "./",
    "./bin/",
    "./include/",
    "./lib -> lib64/",
    "./lib64/",
    "./lib64/include/",
    "./lib64/pkgconfig/",
    "./libexec/",
    "./share/",
    "./share/doc/",
    "./share/man/",
    "./share/orchestra/",
    "./usr/",
    "./usr/include/",
    "./usr/lib/",
}
