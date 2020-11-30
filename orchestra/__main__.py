#!/usr/bin/env python3

from . import main

if __name__ == "__main__":
    return_value = main() or 0
    exit(return_value)
