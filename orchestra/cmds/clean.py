from ..model.configuration import Configuration
import shutil


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("clean", handler=handle_clean, help="Remove build/source directories")
    cmd_parser.add_argument("component")
    cmd_parser.add_argument("--include-sources", "-s", action="store_true", help="Also delete source dir")


def handle_clean(args, config: Configuration):
    build = config.get_build(args.component)
    if input(f"Do you want to clean {build.qualified_name}? [y/N]").lower() != "y":
        return

    build_dir = build.install.environment["BUILD_DIR"]
    shutil.rmtree(build_dir, ignore_errors=True)

    if args.include_sources:
        sources_dir = build.install.environment["SOURCE_DIR"]
        shutil.rmtree(sources_dir, ignore_errors=True)
