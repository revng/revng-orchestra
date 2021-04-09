from textwrap import dedent

from ..orchestra_shim import OrchestraShim

# Values used to override the default orchestra paths
path_overrides = {
    "orchestra_root": "/orchestra/A",
    "source_archives": "/orchestra/B",
    "binary_archives": "/orchestra/C",
    "tmproot": "/orchestra/D",
    "sources_dir": "/orchestra/E",
    "builds_dir": "/orchestra/F",
}


def add_path_overrides(orchestra: OrchestraShim):
    """Adds an overlay which overrides the default orchestra path with fixed ones"""
    orchestra.add_overlay(
        dedent(
            f"""
            #@ load("@ytt:overlay", "overlay")
            #@overlay/match by=overlay.all, missing_ok=True
            #@overlay/match-child-defaults missing_ok=True
            ---
            paths: {path_overrides}
            """
        )
    )
