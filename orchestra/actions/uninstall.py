import os

from loguru import logger


def uninstall(component_name, config):
    index_path = config.installed_component_file_list_path(component_name)
    metadata_path = config.installed_component_metadata_path(component_name)

    # Index and metadata files should be removed last,
    # so an interrupted uninstall can be resumed
    postpone_removal_paths = [
        os.path.relpath(index_path, config.orchestra_root),
        os.path.relpath(metadata_path, config.orchestra_root)
    ]

    with open(index_path) as f:
        paths = f.readlines()

    # Ensure depth first visit by reverse-sorting
    # paths.sort(reverse=True)
    paths = [path.strip() for path in paths]

    for path in paths:
        # Ensure the path is relative to the root
        path = path.lstrip("/")

        if path in postpone_removal_paths:
            continue

        path_to_delete = os.path.join(config.global_env()['ORCHESTRA_ROOT'], path)

        if os.path.isfile(path_to_delete) or os.path.islink(path_to_delete):
            logger.debug(f"Deleting {path_to_delete}")
            os.remove(path_to_delete)
        elif os.path.isdir(path_to_delete):
            if os.listdir(path_to_delete):
                logger.debug(f"Not removing directory {path_to_delete} as it is not empty")
            else:
                logger.debug(f"Deleting directory {path_to_delete}")
                os.rmdir(path_to_delete)

        containing_directory = os.path.dirname(path_to_delete)
        if os.path.exists(containing_directory) and len(os.listdir(containing_directory)) == 0:
            logger.debug(f"Removing empty directory {containing_directory}")
            os.rmdir(containing_directory)

    logger.debug(f"Deleting index file {index_path}")
    os.remove(index_path)

    logger.debug(f"Deleting metadata file {metadata_path}")
    os.remove(metadata_path)
