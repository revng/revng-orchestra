from ..model.index import ComponentIndex


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("components", handler=handle_components)
    cmd_parser.add_argument("component", nargs="?")


def handle_components(args, config, index: ComponentIndex):
    if args.component:
        build = index.get_build(args.component)
        components = {build.component.name: build.component}
    else:
        components = index.components

    for component_name, component in components.items():
        print(f"Component {component_name}")
        for build_name, build in component.builds.items():
            s = f"  Build {build_name}"

            if build.configure:
                external_dependencies = [dep for dep in build.configure.dependencies if dep.build is not build]
                if external_dependencies:
                    s += f" [deps: { ' '.join(dep.build.qualified_name for dep in external_dependencies) }]"

            print(s)
