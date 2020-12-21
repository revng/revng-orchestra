import argparse

build_options = argparse.ArgumentParser(add_help=False)
build_group = build_options.add_argument_group(title="Build options")
build_group.add_argument("--from-source", "-B", action="store_true",
                         help="Build all components from source")
build_group.add_argument("--fallback-build", "-b", action="store_true",
                         help="Build if binary archives are not available")

execution_options = argparse.ArgumentParser(add_help=False)
execution_group = execution_options.add_argument_group(title="Execution options")
execution_group.add_argument("--pretend", "-n", action="store_true",
                             help="Do not execute actions, only print what would be done")
