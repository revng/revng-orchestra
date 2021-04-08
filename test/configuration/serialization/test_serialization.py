from orchestra.model.build import Build
from orchestra.model.component import Component

from ...orchestra_shim import OrchestraShim


def test_build_serialization_rountrip(orchestra: OrchestraShim):
    """Checks that Build.serialize can be deserialized into an equivalent object"""
    config = orchestra.configuration

    component_G = config.components["component_G"]
    build1 = component_G.builds["build0"]

    serialized_build = build1.serialize()
    build2 = Build("build0", serialized_build, component_G, config)

    assert build1.build_hash == build2.build_hash


def test_component_serialization_rountrip(orchestra: OrchestraShim):
    """Checks that Component.serialize can be deserialized into an equivalent object"""
    config = orchestra.configuration

    component_G1 = config.components["component_G"]

    serialized_component = component_G1.serialize()
    component_G2 = Component("component_G", serialized_component, config)
    component_G2.resolve_dependencies(config)

    assert component_G1.self_hash == component_G2.self_hash
    assert component_G1.recursive_hash == component_G2.recursive_hash
