import json

from orchestra.model._hash import hash
from ..orchestra_shim import OrchestraShim


def test_build_serialize(orchestra: OrchestraShim):
    """Checks that Build.serialize returns the expected data"""
    orchestra("update")
    build = orchestra.configuration.components["component_C"].builds["build0"]

    expected_value = {
        "configure": build.configure.script,
        "install": build.install.script,
        "dependencies": build._explicit_dependencies,
        "build_dependencies": build._explicit_build_dependencies,
        "ndebug": build.ndebug,
    }
    assert build.serialize() == expected_value


def test_build_hash(orchestra: OrchestraShim):
    """Checks that Build computes the expected hash"""
    orchestra("update")
    build = orchestra.configuration.components["component_C"].builds["build0"]

    computed_expected_hash = hash(json.dumps(build.serialize(), sort_keys=True))
    assert build.build_hash == computed_expected_hash


def test_component_serialize(orchestra: OrchestraShim):
    """Checks that Component.serialize returns the expected data"""
    orchestra("update")
    component = orchestra.configuration.components["component_C"]
    expected_value = {
        "license": component.license,
        "skip_post_install": component.skip_post_install,
        "add_to_path": component.add_to_path,
        "repository": component.repository,
        "default_build": component.default_build_name,
        "builds": {b.name: b.serialize() for b in component.builds.values()},
    }
    assert component.serialize() == expected_value


def test_component_self_hash_material(orchestra: OrchestraShim):
    """Checks that Component returns the expected data used for computing self_hash"""
    orchestra("update")
    component = orchestra.configuration.components["component_C"]
    builds = [
        component.builds["build0"],
    ]

    to_hash = "".join(b.build_hash for b in builds)
    commit = component.commit()
    if commit:
        to_hash += commit

    assert component._self_hash_material() == to_hash


def test_component_self_hash(orchestra: OrchestraShim):
    """Checks that Component computes the expected self hash"""
    orchestra("update")
    component = orchestra.configuration.components["component_C"]

    expected_hash = hash(component._self_hash_material())
    assert component.self_hash == expected_hash


def test_component_transitive_dependencies(orchestra: OrchestraShim):
    """Checks that Component collects its transitive dependencies correctly"""
    # WARN: do NOT replace with multiple accesses to orchestra.configuration as it would instantiate different objects
    config = orchestra.configuration
    expected_transitive_dependencies = {
        config.components["component_A"],
        config.components["component_B"],
        config.components["component_C"],
    }

    assert config.components["component_C"]._transitive_dependencies() == expected_transitive_dependencies


def test_component_recursive_hash_material(orchestra: OrchestraShim):
    """Checks that Component returns the expected data used for computing recursive_hash"""
    config = orchestra.configuration
    component = config.components["component_C"]

    expected_hash_material = ""
    for d in sorted(component._transitive_dependencies(), key=lambda c: c.name):
        expected_hash_material += d.self_hash

    assert component._recursive_hash_material() == expected_hash_material


def test_component_recursive_hash(orchestra: OrchestraShim):
    """Checks that Components computes the expected recursive_hash"""
    config = orchestra.configuration
    component = config.components["component_C"]
    assert hash(component._recursive_hash_material()) == component.recursive_hash
