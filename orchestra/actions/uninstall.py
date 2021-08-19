import os
import stat

from loguru import logger

from ..model.install_metadata import (
    load_file_list,
    installed_component_file_list_path,
    installed_component_metadata_path,
)


def uninstall(component_name, config):
    index_path = installed_component_file_list_path(component_name, config)
    metadata_path = installed_component_metadata_path(component_name, config)

    # Index and metadata files should be removed last,
    # so an interrupted uninstall can be resumed
    postpone_removal_paths = [
        os.path.relpath(index_path, config.orchestra_root),
        os.path.relpath(metadata_path, config.orchestra_root),
    ]

    paths = load_file_list(component_name, config)

    # Ensure depth first visit by reverse-sorting
    # paths.sort(reverse=True)
    paths = [path.strip() for path in paths]

    orchestra_root = config.global_env()["ORCHESTRA_ROOT"]

    for path in paths:
        # Ensure the path is relative to the root
        path = path.lstrip("/")

        if path in postpone_removal_paths:
            continue

        path_to_delete = os.path.join(orchestra_root, path)
        try:
            stat_result = os.stat(path_to_delete, follow_symlinks=False)
            stat_mode = stat_result.st_mode
        except FileNotFoundError:
            continue

        if stat.S_ISREG(stat_mode) or stat.S_ISLNK(stat_mode):
            logger.debug(f"Deleting {path_to_delete}")
            os.remove(path_to_delete)
        elif stat.S_ISDIR(stat_mode):
            if os.listdir(path_to_delete):
                logger.debug(f"Not removing directory {path_to_delete} as it is not empty")
            else:
                logger.debug(f"Deleting directory {path_to_delete}")
                os.rmdir(path_to_delete)

        containing_directory = os.path.dirname(path_to_delete)
        # not any(scandir(path)) is a fast way to tell if a directory is empty
        if os.path.exists(containing_directory) and not any(os.scandir(containing_directory)):
            logger.debug(f"Removing empty directory {containing_directory}")
            os.rmdir(containing_directory)

    logger.debug(f"Deleting index file {index_path}")
    os.remove(index_path)

    logger.debug(f"Deleting metadata file {metadata_path}")
    os.remove(metadata_path)
