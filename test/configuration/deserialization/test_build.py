from orchestra.actions.any_of import AnyOfAction

from ...orchestra_shim import OrchestraShim


def test_build_deserialization(orchestra: OrchestraShim):
    """Checks that Build deserialization produces the expected objects"""
    config = orchestra.configuration
    # Components used as dependencies
    component_A = config.components["component_A"]
    component_B = config.components["component_B"]
    component_C = config.components["component_C"]
    component_D = config.components["component_D"]
    component_E = config.components["component_E"]
    component_F = config.components["component_F"]

    # Component used to test against
    component_G = config.components["component_G"]
    build = component_G.builds["build0"]
    serialized_build = config.parsed_yaml["components"]["component_G"]["builds"]["build0"]

    assert build.install.script == serialized_build["install"]
    assert build.configure.script == serialized_build["configure"]
    assert build.ndebug == serialized_build["ndebug"]
    assert build._explicit_dependencies == serialized_build["dependencies"]
    assert build._explicit_build_dependencies == serialized_build["build_dependencies"]

    assert build.configure.dependencies_for_hash == {
        component_A.builds["build0"].install,
        AnyOfAction({b.install for b in component_B.builds.values()}, component_B.builds["build1"].install),
        component_C.builds["build1"].install,
        component_D.builds["build0"].install,
        AnyOfAction({b.install for b in component_E.builds.values()}, component_E.builds["build1"].install),
        component_F.builds["build1"].install,
        component_G.clone,
    }

    assert build.configure.dependencies == {
        component_A.builds["build0"].install,
        AnyOfAction({b.install for b in component_B.builds.values()}, component_B.builds["build1"].install),
        component_C.builds["build1"].install,
        component_D.builds["build0"].install,
        AnyOfAction({b.install for b in component_E.builds.values()}, component_E.builds["build1"].install),
        component_F.builds["build1"].install,
        component_G.clone,
    }

    assert build.install.dependencies_for_hash == {
        component_A.builds["build0"].install,
        AnyOfAction({b.install for b in component_B.builds.values()}, component_B.builds["build1"].install),
        component_C.builds["build1"].install,
        build.configure,
    }

    assert build.install.dependencies == {
        component_A.builds["build0"].install,
        AnyOfAction({b.install for b in component_B.builds.values()}, component_B.builds["build1"].install),
        component_C.builds["build1"].install,
        build.configure,
    }
