import networkx as nx
from loguru import logger

from .common import build_options
from ..executor import Executor
from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("graph",
                                          handler=handle_graph,
                                          help="Print dependency graph (dot format)",
                                          parents=[build_options]
                                          )
    cmd_parser.add_argument("component", nargs="?")
    cmd_parser.add_argument("--all-builds", action="store_true",
                            help="Include all builds instead of only the default one.\n"
                                 "Can't be used with --solved")

    cmd_parser.add_argument("--solved", "-s", action="store_true",
                            help="Print the solved dependency graph that would be used to schedule actions")
    cmd_parser.add_argument("--no-remove-unreachable", action="store_true",
                            help="Don't remove unreachable actions")
    cmd_parser.add_argument("--no-simplify-anyof", action="store_true",
                            help="Don't remove choices")
    cmd_parser.add_argument("--no-remove-satisfied-leaves", action="store_true",
                            help="Don't remove satisfied leaves")
    cmd_parser.add_argument("--no-transitive-reduction", action="store_true",
                            help="Don't perform transitive reduction")
    cmd_parser.add_argument("--no-force", action="store_true",
                            help="Don't force execution of the root action")


def handle_graph(args):
    config = Configuration(fallback_to_build=args.fallback_build,
                           force_from_source=args.from_source,
                           use_config_cache=args.config_cache,
                           )
    if args.component:
        build = config.get_build(args.component)

        if not build:
            suggested_component_name = config.get_suggested_component_name(args.component)
            logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
            return 1

        actions = [build.install]
    else:
        actions = set()
        for component in config.components.values():
            if args.all_builds:
                for build in component.builds.values():
                    actions.add(build.install)
            else:
                actions.add(component.default_build.install)

    executor = Executor(actions, no_force=args.no_force)

    if not args.solved:
        graph = executor._create_initial_dependency_graph()
    else:
        graph = executor._create_dependency_graph(
            remove_unreachable=not args.no_remove_unreachable,
            simplify_anyof=not args.no_simplify_anyof,
            remove_satisfied=not args.no_remove_satisfied_leaves,
            transitive_reduction=not args.no_transitive_reduction
        )
    graphviz_format = nx.nx_agraph.to_agraph(graph)
    graphviz_format.graph_attr["splines"] = "ortho"
    graphviz_format.node_attr["shape"] = "box"
    print(graphviz_format)

    return 0
