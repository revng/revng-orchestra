import pytest

from ..orchestra_shim import OrchestraShim


def test_simple_schedule(orchestra: OrchestraShim):
    """Checks that a simple schedule can run"""
    orchestra("graph", "-b", "component_A")
    orchestra("graph", "-b", "-s", "component_A")
    orchestra("install", "-b", "component_A")


def test_avoid_cycle(orchestra: OrchestraShim):
    """Checks that orchestra is able to pick the correct dependency, even when the preferred dependency originates a
    cycle
    """
    orchestra("graph", "-b", "component_with_cyclic_dependency_A")
    orchestra("graph", "-b", "-s", "component_with_cyclic_dependency_A")
    orchestra("install", "-b", "component_with_cyclic_dependency_A")


def test_reject_simple_cycle(orchestra: OrchestraShim):
    """Checks that a simple cyclic dependency raises an exception when installing, but not when printing the graph"""
    # Print unsolved graph
    orchestra("graph", "-b", "component_cyclic_A")

    # Print solved graph
    orchestra("graph", "-b", "-s", "component_cyclic_A")

    # Install
    with pytest.raises(Exception):
        orchestra("install", "-b", "component_cyclic_A")


def test_reject_choice_cycle(orchestra: OrchestraShim):
    """Checks that a choice which cannot be taken without generating an unsatisfied cycle raises an exception when
    installing and when printing the solved graph, but not when printing the unsolved graph
    """
    # Print unsolved graph
    orchestra("graph", "-b", "component_cyclic_C")

    # Print solved graph
    with pytest.raises(Exception):
        orchestra("graph", "-b", "-s", "component_cyclic_C")

    # Install
    with pytest.raises(Exception):
        orchestra("install", "-b", "component_cyclic_A")


def test_toolchain_bootstrap(orchestra: OrchestraShim):
    """Checks that orchestra is able to handle a dependency graph like the one required by a toolchain bootstrap"""
    # Print unsolved graph
    orchestra("graph", "-b", "gcc")

    # Print solved graph
    orchestra("graph", "-b", "-s", "gcc")

    # Install
    orchestra("install", "-b", "gcc")


def test_same_component_ordering(orchestra: OrchestraShim):
    """Checks that the edges added to enforce an order between installs of the same component do not introduce cycles"""
    # Print unsolved graph
    print("Unsolved graph")
    orchestra("graph", "-b", "component_sco_A")

    # Print solved graph
    print("Solved graph")
    orchestra("graph", "-b", "-s", "component_sco_A")

    # Install
    orchestra("install", "-b", "component_sco_A")
