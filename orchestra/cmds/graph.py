from loguru import logger

from . import SubCommandParser
from .common import build_options
from ..model.configuration import Configuration


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd(
        "graph",
        handler=handle_graph,
        help="Print dependency graph (dot format)",
        parents=[build_options],
    )
    cmd_parser.add_argument("components", nargs="*")
    cmd_parser.add_argument(
        "--all-builds",
        action="store_true",
        help="Include all builds instead of only the default one.\nCan't be used with --solved",
    )
    cmd_parser.add_argument(
        "--solved",
        "-s",
        action="store_true",
        help="Print the solved dependency graph that would be used to schedule actions",
    )
    cmd_parser.add_argument(
        "--no-remove-unreachable",
        action="store_true",
        help="Don't remove unreachable actions",
    )
    cmd_parser.add_argument("--no-simplify-anyof", action="store_true", help="Don't remove choices")
    cmd_parser.add_argument(
        "--no-remove-satisfied-leaves",
        action="store_true",
        help="Don't remove satisfied leaves",
    )
    cmd_parser.add_argument(
        "--no-transitive-reduction",
        action="store_true",
        help="Don't perform transitive reduction",
    )
    cmd_parser.add_argument(
        "--no-force",
        action="store_true",
        help="Don't force execution of the root action",
    )
    cmd_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Don't color the graph",
    )


def handle_graph(args):
    config = Configuration(
        fallback_to_build=args.fallback_build,
        force_from_source=args.from_source,
        use_config_cache=args.config_cache,
    )

    actions = set()

    if args.components:
        for component in args.components:
            build = config.get_build(component)
            if not build:
                suggested_component_name = config.get_suggested_component_name(component)
                logger.error(f"Component {component} not found! Did you mean {suggested_component_name}?")
                return 1

            actions.add(build.install)
    else:
        for component in config.components.values():
            if args.all_builds:
                for build in component.builds.values():
                    actions.add(build.install)
            else:
                actions.add(component.default_build.install)

    from ..executor import Executor

    executor = Executor(actions, no_force=args.no_force)

    if not args.solved:
        graph = executor._create_initial_dependency_graph()
    else:
        graph = executor._create_dependency_graph(
            remove_unreachable=not args.no_remove_unreachable,
            simplify_anyof=not args.no_simplify_anyof,
            remove_satisfied=not args.no_remove_satisfied_leaves,
            transitive_reduction=not args.no_transitive_reduction,
        )
    if not args.no_color:
        from ..actions.graph_util import assign_style

        assign_style(graph)
    import networkx as nx

    graphviz_format = nx.nx_pydot.to_pydot(graph)
    graphviz_format.set_splines("ortho")
    graphviz_format.set_node_defaults(shape="box")
    print(graphviz_format)

    return 0
