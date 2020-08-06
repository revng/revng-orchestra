from ..model.index import ComponentIndex
from ..executor import Executor


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("configure", handler=handle_configure)
    cmd_parser.add_argument("component")
    cmd_parser.add_argument("--force", action="store_true", help="Force execution of the root action")


def handle_configure(args, config, index: ComponentIndex):
    build = index.get_build(args.component)
    executor = Executor(show_output=args.show_output)
    executor.run(build.configure, force=args.force)
