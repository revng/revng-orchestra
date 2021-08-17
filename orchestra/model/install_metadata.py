import json
import os
from typing import List, Optional

from . import build as bld
from . import configuration


class InstallMetadata:
    def __init__(
        self,
        component_name,
        build_name,
        recursive_hash,
        *,
        source=None,
        manually_installed=None,
        install_time=None,
        binary_archive_path=None,
    ):
        self.component_name = component_name
        self.build_name = build_name
        self.recursive_hash = recursive_hash
        self.source = source
        self.manually_installed = manually_installed
        self.install_time = install_time
        self.binary_archive_path = binary_archive_path

    def serialize(self):
        assert all(
            prop is not None
            for prop in [
                self.source,
                self.binary_archive_path,
                self.manually_installed,
                self.install_time,
            ]
        ), "Trying to serialize incomplete metadata"

        return self.__dict__


def _deserialize_metadata(serialized_metadata) -> InstallMetadata:
    return InstallMetadata(
        serialized_metadata["component_name"],
        serialized_metadata["build_name"],
        serialized_metadata["recursive_hash"],
        source=serialized_metadata.get("source"),
        manually_installed=serialized_metadata.get("manually_installed"),
        install_time=serialized_metadata.get("install_time"),
        binary_archive_path=serialized_metadata.get("binary_archive_path"),
    )


def init_metadata_from_build(build: "bld.Build") -> InstallMetadata:
    return InstallMetadata(build.component.name, build.name, build.component.recursive_hash)


def is_installed(
    config: "configuration.Configuration",
    wanted_component_name: str,
    wanted_build=None,
    wanted_recursive_hash=None,
):
    """Returns true if the component with the given properties is installed.
    :param config: a Configuration instance
    :param wanted_component_name: wanted component name
    :param wanted_build: wanted build name (None means any build)
    :param wanted_recursive_hash: wanted build hash (None means any hash)
    """
    metadata = load_metadata(wanted_component_name, config)
    if metadata is None:
        return False

    correct_build = wanted_build is None or metadata.build_name == wanted_build
    correct_hash = wanted_recursive_hash is None or metadata.recursive_hash == wanted_recursive_hash

    return correct_build and correct_hash


def load_metadata(component_name, config: "configuration.Configuration") -> Optional[InstallMetadata]:
    """Returns the metadata for an installed component.
    If the component is not installed, returns None
    """
    metadata_path = installed_component_metadata_path(component_name, config)
    if not os.path.exists(metadata_path):
        return None

    with open(metadata_path) as f:
        serialized_metadata = json.load(f)

    return _deserialize_metadata(serialized_metadata)


def save_metadata(metadata: InstallMetadata, config: "configuration.Configuration"):
    """Writes metadata to disk"""
    _create_metadata_dir(config)

    metadata_path = installed_component_metadata_path(metadata.component_name, config)
    with open(metadata_path, "w") as f:
        json.dump(metadata.serialize(), f)


def load_file_list(component_name: str, config: "configuration.Configuration") -> Optional[List[str]]:
    """Returns a list of the files associated with an installed component.
    If the component is not installed, returns None
    """
    file_list_path = installed_component_file_list_path(component_name, config)
    with open(file_list_path) as f:
        paths = f.read().splitlines()
    return paths


def save_file_list(component_name: str, file_list: List[str], config: "configuration.Configuration"):
    """Writes the installed file list to disk"""
    _create_metadata_dir(config)

    file_list_path = installed_component_file_list_path(component_name, config)
    with open(file_list_path, "w") as f:
        new_files = [f"{f}\n" for f in file_list]
        f.writelines(new_files)


def _create_metadata_dir(config: "configuration.Configuration"):
    # Write file metadata and index
    metadata_dir_path = config.installed_component_metadata_dir
    os.makedirs(metadata_dir_path, exist_ok=True)


def installed_component_file_list_path(component_name: str, config: "configuration.Configuration") -> str:
    """Returns the path of the index containing the list of installed files of a component"""
    return os.path.join(config.installed_component_metadata_dir, component_name.replace("/", "_") + ".idx")


def installed_component_metadata_path(component_name: str, config: "configuration.Configuration") -> str:
    """Returns the path of the file containing metadata about an installed component"""
    return os.path.join(config.installed_component_metadata_dir, component_name.replace("/", "_") + ".json")


def installed_component_license_path(component_name: str, config: "configuration.Configuration") -> str:
    """Returns the path of the file containing the license of an installed component"""
    return os.path.join(config.installed_component_metadata_dir, component_name.replace("/", "_") + ".license")
