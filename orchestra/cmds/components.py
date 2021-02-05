from fnmatch import fnmatch
from urllib.parse import urlparse

from loguru import logger

from ..model.configuration import Configuration
from ..util import get_installed_metadata, get_installed_build


def normalize_repository_url(url):
    # Drop credentials
    if url.startswith("https://") or url.startswith("http://"):
        url = urlparse(url)
        url = url._replace(netloc=url.hostname).geturl()

    # Add .git suffix
    if not url.endswith(".git"):
        url = url + ".git"

    return url


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("components", handler=handle_components, help="List components")
    cmd_parser.add_argument("component", nargs="?")
    cmd_parser.add_argument("--installed", action="store_true", help="Only print installed components")
    cmd_parser.add_argument("--not-installed", action="store_true", help="Only print not installed components")
    cmd_parser.add_argument("--deps", action="store_true", help="Print dependencies")
    cmd_parser.add_argument("--hashes", action="store_true", help="Show hashes")
    cmd_parser.add_argument("--repository-url", help="Show components from this repository URL")
    cmd_parser.add_argument("--branch", help="Show components using this branch (jolly expression)")


def handle_components(args):
    config = Configuration(use_config_cache=args.config_cache)
    if args.component:
        build = config.get_build(args.component)

        if not build:
            suggested_component_name = config.get_suggested_component_name(args.component)
            logger.error(f"Component {args.component} not found! Did you mean {suggested_component_name}?")
            return 1

        components = {build.component.name: build.component}
    else:
        components = config.components

    repository_filter = None
    if args.repository_url:
        repository_filter = normalize_repository_url(args.repository_url)

    for component_name, component in components.items():
        # Filter by repository URL
        if repository_filter:
            if not component.clone:
                continue
            repository = component.clone.repository
            if not any(remote_base_url
                       for remote_base_url
                       in config.remotes.values()
                       if normalize_repository_url(f"{remote_base_url}/{repository}") == repository_filter):
                continue

        # Filter by branch
        if args.branch:
            if not component.clone:
                continue

            branch, _ = component.clone.branch()
            if not fnmatch(branch, args.branch):
                continue

        metadata = get_installed_metadata(component_name, config)
        is_installed = metadata is not None
        manually_installed = is_installed and metadata.get("manually_installed", False)
        installed_build = metadata and metadata.get("build_name")
        if args.installed and not is_installed:
            continue
        if args.not_installed and is_installed:
            continue

        component_infos = []
        if args.hashes:
            component_infos.append(f"hash: {component.self_hash}")
            component_infos.append(f"recursive hash: {component.recursive_hash}")
        component_infos_s = stringify_infos(component_infos)

        print(f"Component {component_name} {component_infos_s}")
        for build_name, build in component.builds.items():
            build_infos = []
            if installed_build == build_name:
                if manually_installed:
                    build_infos.append("installed manually")
                else:
                    build_infos.append("installed as dependency")

            if build is component.default_build:
                build_infos.append("default")

            if build.configure and args.deps:
                dependencies = [dep for dep in build.configure.dependencies]
                if dependencies:
                    build_infos.append(f"config deps: {' '.join(d.name_for_components for d in dependencies)}")

            if build.install and args.deps:
                dependencies = [dep for dep in build.install.dependencies]
                if dependencies:
                    build_infos.append(f"install deps: {' '.join(d.name_for_components for d in dependencies)}")

            build_infos_s = stringify_infos(build_infos)
            print(f"  Build {build_name} {build_infos_s}")

        print()


def stringify_infos(infos):
    return " ".join(f"[{i}]" for i in infos)
