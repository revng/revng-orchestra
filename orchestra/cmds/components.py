from ..model.configuration import Configuration
from ..util import get_installed_build


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("components", handler=handle_components, help="List components")
    cmd_parser.add_argument("component", nargs="?")
    cmd_parser.add_argument("--installed", action="store_true", help="Only print installed components")
    cmd_parser.add_argument("--not-installed", action="store_true", help="Only print not installed components")
    cmd_parser.add_argument("--deps", action="store_true", help="Print dependencies")


def handle_components(args, config: Configuration):
    if args.component:
        build = config.get_build(args.component)
        components = {build.component.name: build.component}
    else:
        components = config.components

    for component_name, component in components.items():
        installed_build = get_installed_build(component_name, config)
        if args.installed and installed_build \
                or args.not_installed and installed_build is None \
                or not args.installed and not args.not_installed:
            print(f"Component {component_name}")
            for build_name, build in component.builds.items():
                infos = []
                if installed_build == build_name:
                    infos.append("installed")
                if build is component.default_build:
                    infos.append("default")

                if build.configure and args.deps:
                    dependencies = [dep for dep in build.configure.dependencies]
                    if dependencies:
                        infos.append(f"config deps: {' '.join(d.name_for_components for d in dependencies)}")

                if build.install and args.deps:
                    dependencies = [dep for dep in build.install.dependencies if dep.build is not build]
                    if dependencies:
                        infos.append(f"install deps: {' '.join(d.name_for_components for d in dependencies)}")

                infos_s = " ".join(f"[{i}]" for i in infos)

                s = f"  Build {build_name} {infos_s}"

                print(s)
            print()
