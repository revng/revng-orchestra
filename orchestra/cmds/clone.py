from ..model.configuration import Configuration
from ..executor import Executor


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("clone", handler=handle_clone)
    cmd_parser.add_argument("component")
    cmd_parser.add_argument("--force", action="store_true", help="Force execution of the root action")


def handle_clone(args, config: Configuration):
    build = config.get_build(args.component)
    executor = Executor(args)
    executor.run(build.clone, force=args.force)
