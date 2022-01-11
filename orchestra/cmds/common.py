import argparse

LFS_RETRIES_DEFAULT = 3

build_options = argparse.ArgumentParser(add_help=False)
build_group = build_options.add_argument_group(title="Build options")
build_group.add_argument("--from-source", "-B", action="store_true", help="Build all components from source")
build_group.add_argument(
    "--fallback-build",
    "-b",
    action="store_true",
    help="Build if binary archives are not available",
)
build_group.add_argument(
    "--discard-build-directories",
    action="store_true",
    help="Discards build directories of the involved components after a successful build. Previously existing build "
    "directories are used and then deleted. Use `orc clean` to remove them in advance.",
)
build_group.add_argument("--test", action="store_true", help="Run the test suite after building")

execution_options = argparse.ArgumentParser(add_help=False)
execution_group = execution_options.add_argument_group(title="Execution options")
execution_group.add_argument(
    "--pretend",
    "-n",
    action="store_true",
    help="Do not execute actions, only print what would be done",
)

execution_group.add_argument(
    "--lfs-retries",
    metavar="N",
    type=int,
    default=LFS_RETRIES_DEFAULT,
    help=f"Retry fetching binary archives up to N times before giving up. Defaults to {LFS_RETRIES_DEFAULT}",
)
