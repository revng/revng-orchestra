from ..paths_common import add_path_overrides, path_overrides
from ...orchestra_shim import OrchestraShim

# Mapping from the name of a path override in the yaml to the name of the property in Configuration
# Only specified where the name is different
yaml_name_to_configuration_property_name = {
    "binary_archives": "binary_archives_dir",
}


def test_user_paths(orchestra: OrchestraShim):
    """Checks that the user is able to override orchestra paths and Configuration properties reflect that"""
    add_path_overrides(orchestra)
    config = orchestra.configuration
    for name, val in path_overrides.items():
        configuration_property_name = yaml_name_to_configuration_property_name.get(name, name)
        actual_value = getattr(config, configuration_property_name)
        assert actual_value == val, f"Expected path '{name}' to be {val}, was {actual_value}"
