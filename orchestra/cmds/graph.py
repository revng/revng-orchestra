from ..model.index import ComponentIndex


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("graph", handler=handle_graph)
    cmd_parser.add_argument("component", nargs="?")
    cmd_parser.add_argument("--all-builds", action="store_true", help="Include all builds instead of only the default one.")


def handle_graph(args, config, index: ComponentIndex):
    # TODO: this function prints duplicate edges
    if args.component:
        actions = [index.get_build(args.component).install]
    else:
        actions = set()
        for component in index.components.values():
            if args.all_builds:
                for build in component.builds.values():
                    actions.add(build.install)
            else:
                actions.add(component.default_build.install)

    print("digraph dependency_graph {")
    print("  splines=ortho")
    print_dependencies(actions)
    print("}")


def print_dependencies(actions):
    def _print_dependencies(action, already_visited_actions):
        if action in already_visited_actions:
            return

        print(f'  "{action.qualified_name}"[ shape=box ];')
        for d in action.dependencies:
            print(f'  "{d.qualified_name}" -> "{action.qualified_name}";')

        already_visited_actions.add(action)

        for d in action.dependencies:
            _print_dependencies(d, already_visited_actions)

    already_visited_actions = set()
    for action in actions:
        _print_dependencies(action, already_visited_actions)
