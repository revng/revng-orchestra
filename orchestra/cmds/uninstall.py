from ..model.index import ComponentIndex
from ..executor import Executor


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("uninstall", handler=handle_uninstall)
    cmd_parser.add_argument("component")


def handle_uninstall(args, config, index: ComponentIndex):
    build = index.get_build(args.component)
    executor = Executor(show_output=args.show_output)
    executor.run(build.uninstall, force=args.force)
