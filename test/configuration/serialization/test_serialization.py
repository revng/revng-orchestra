from orchestra.model.build import Build
from orchestra.model.component import Component

from ...orchestra_shim import OrchestraShim


def test_component_serialization_rountrip(orchestra: OrchestraShim):
    """Checks that Component.serialize can be deserialized into an equivalent object"""
    config = orchestra.configuration

    component_G1 = config.components["component_G"]

    serialized_component = component_G1.serialize()
    component_G2 = Component("component_G", serialized_component, config)
    component_G2.resolve_dependencies(config)

    assert component_G1.recursive_hash == component_G2.recursive_hash
