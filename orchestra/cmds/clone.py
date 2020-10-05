from ..model.configuration import Configuration
from ..executor import Executor


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("clone", handler=handle_clone, help="Clone a component")
    cmd_parser.add_argument("component")
    cmd_parser.add_argument("--force", action="store_true", help="Force execution of the root action")


def handle_clone(args, config: Configuration):
    build = config.get_build(args.component)
    if not build.clone:
        print("This component does not have a git repository configured!")
        return
    executor = Executor(args)
    executor.run(build.clone, force=args.force)
