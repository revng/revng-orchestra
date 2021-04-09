from textwrap import dedent

import pytest

from ..orchestra_shim import OrchestraShim


def test_minimum_version_ok(orchestra: OrchestraShim):
    """Checks that the minimum version field is handled correctly"""
    orchestra.add_overlay(
        dedent(
            """
            #@ load("@ytt:overlay", "overlay")
            #@overlay/match by=overlay.all, missing_ok=True
            #@overlay/match-child-defaults missing_ok=True
            ---
            min_orchestra_version: 3.0.0    
            """
        )
    )
    orchestra("components")


def test_validate_minimum_version(orchestra: OrchestraShim):
    """Checks that orchestra raises an error if the minimum version is higher than the current version"""
    orchestra.add_overlay(
        dedent(
            """
            #@ load("@ytt:overlay", "overlay")
            #@overlay/match by=overlay.all, missing_ok=True
            #@overlay/match-child-defaults missing_ok=True
            ---
            min_orchestra_version: 4.0.0    
            """
        )
    )

    with pytest.raises(Exception):
        orchestra("components")
