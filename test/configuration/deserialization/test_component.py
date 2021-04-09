from orchestra.actions.any_of import AnyOfAction

from ...orchestra_shim import OrchestraShim


def test_component_deserialization(orchestra: OrchestraShim):
    """Checks that Component deserialization produces the expected objects"""
    config = orchestra.configuration
    component_G = config.components["component_G"]
    serialized_component = config.parsed_yaml["components"]["component_G"]

    assert component_G.default_build_name == serialized_component["default_build"]
    assert component_G.default_build == component_G.builds[component_G.default_build_name]
    assert component_G.license == serialized_component["license"]
    assert component_G.binary_archives == serialized_component["binary_archives"]
    assert component_G.repository == serialized_component["repository"]
    assert component_G.build_from_source == serialized_component["build_from_source"]
    assert component_G.skip_post_install == serialized_component["skip_post_install"]
    assert component_G.add_to_path == serialized_component["add_to_path"]

    # Build deserialization is tested separately
    assert component_G.builds.keys() == serialized_component["builds"].keys()
