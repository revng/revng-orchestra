import json
from fnmatch import fnmatch
from urllib.parse import urlparse

from loguru import logger

from . import SubCommandParser
from ..model.configuration import Configuration
from ..model.install_metadata import load_metadata, is_installed


def normalize_repository_url(url):
    # Drop credentials
    if url.startswith("https://") or url.startswith("http://"):
        url = urlparse(url)
        url = url._replace(netloc=url.hostname).geturl()

    # Add .git suffix
    if not url.endswith(".git"):
        url = url + ".git"

    return url


def install_subcommand(sub_argparser: SubCommandParser):
    cmd_parser = sub_argparser.add_subcmd("components", handler=handle_components, help="List components")
    cmd_parser.add_argument("component", nargs="?")
    cmd_parser.add_argument("--installed", action="store_true", help="Only print installed components")
    cmd_parser.add_argument(
        "--not-installed",
        action="store_true",
        help="Only print not installed components",
    )
    cmd_parser.add_argument("--deps", action="store_true", help="Print dependencies")
    cmd_parser.add_argument("--hashes", action="store_true", help="Show hashes")
    cmd_parser.add_argument("--repository-url", help="Show components from this repository URL")
    cmd_parser.add_argument("--branch", help="Show components using this branch (jolly expression)")
    cmd_parser.add_argument("--json", action="store_true", help="Print infos as JSON")


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

    components_to_print = set()

    for component_name, component in components.items():
        # Filter by repository URL
        if repository_filter:
            if not component.clone:
                continue
            repository = component.clone.repository
            if not any(
                remote_base_url
                for remote_base_url in config.remotes.values()
                if normalize_repository_url(f"{remote_base_url}/{repository}") == repository_filter
            ):
                continue

        # Filter by branch
        if args.branch:
            if not component.clone:
                continue

            branch, _ = component.clone.branch()
            if branch is None or not fnmatch(branch, args.branch):
                continue

        # Filter by install status
        component_is_installed = is_installed(config, component_name)
        if args.installed and not component_is_installed or args.not_installed and component_is_installed:
            continue

        components_to_print.add(component)

    if args.json:
        print_json(components_to_print, config)
    else:
        print_human_readable(components_to_print, config, args)
    return 0


def print_json(components, config):
    components_json = []
    for component in components:
        component_name = component.name
        metadata = load_metadata(component_name, config)
        is_installed = metadata is not None
        manually_installed = is_installed and metadata.manually_installed
        installed_build = metadata and metadata.build_name
        component_info = {
            "name": component.name,
            "license": component.license,
            "repository": component.repository,
            "build_from_source": component.build_from_source,
            "skip_post_install": component.skip_post_install,
            "add_to_path": component.add_to_path,
            "installed": is_installed,
            "manually_installed": manually_installed,
            "installed_build_name": installed_build,
            "hash": component.self_hash,
            "recursive_hash": component.recursive_hash,
            "default_build": component.default_build.name,
            "builds": {},
        }

        if component.clone:
            branch_name, branch_commit = component.clone.branch()
            component_info["head_branch_name"] = branch_name
            component_info["head_commit"] = branch_commit

        for build_name, build in component.builds.items():
            build_info = {
                "installed": installed_build == build_name,
                "default": build is component.default_build,
                "qualified_name": build.qualified_name,
                "ndebug": build.ndebug,
            }
            if build.configure:
                build_info["dependencies"] = [d.name_for_components for d in build.configure.dependencies]

            if build.install:
                build_info["build_dependencies"] = [d.name_for_components for d in build.install.dependencies]

            component_info["builds"][build_name] = build_info
        components_json.append(component_info)
    print(json.dumps(components_json))


def print_human_readable(components, config, args):
    for component in components:
        component_name = component.name
        metadata = load_metadata(component_name, config)

        component_infos = []
        if args.hashes:
            component_infos.append(f"hash: {component.self_hash}")
            component_infos.append(f"recursive hash: {component.recursive_hash}")
        component_infos_s = stringify_infos(component_infos)

        if component.commit():
            component_infos.append(f"commit: {component.commit()}")
        if component.branch():
            component_infos.append(f"branch: {component.branch()}")

        builds_rows = []
        for build_name, build in component.builds.items():
            build_infos = []
            if metadata is not None and metadata.build_name == build_name:
                if metadata.manually_installed:
                    build_infos.append("installed_manually")
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
            builds_rows.append(f"Build {build_name} {build_infos_s}")

        print(f"Component {component_name} {component_infos_s}")
        for row in builds_rows:
            print(f"  {row}")

        print()


def stringify_infos(infos):
    return " ".join(f"[{i}]" for i in infos)
