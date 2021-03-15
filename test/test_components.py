import json

from .orchestra_shim import OrchestraShim


def test_components(orchestra: OrchestraShim):
    """Checks that `orchestra components` does not crash
    Regression test for https://github.com/revng/orchestra/issues/18
    """
    orchestra("components")


def test_components_json_output_format(orchestra: OrchestraShim, capsys):
    """Checks that `orchestra components --json` produces the expected output"""
    orchestra("update")
    capsys.readouterr()

    orchestra("components", "--json", "component_A")
    out, err = capsys.readouterr()

    parsed_output = json.loads(out)
    assert parsed_output == [
        {
            "name": "component_A",
            "installed": False,
            "manually_installed": False,
            "installed_build_name": None,
            "hash": "5f3eb643f573d96dec43b06e9dd1e73c5e7bb9dc",
            "recursive_hash": "d27e94a0fec100fd4fbdc08e4b8967e32614f222",
            "default_build": "default",
            "builds": {
                "default": {
                    "installed": False,
                    "default": True,
                    "qualified_name": "component_A@default",
                    "config_deps": [],
                    "install_deps": [],
                }
            },
        }
    ]
