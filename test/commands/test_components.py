import json
import jsonschema
import yaml
import pkg_resources

from ..orchestra_shim import OrchestraShim


def test_components(orchestra: OrchestraShim):
    """Checks that `orchestra components` does not crash.
    Regression test for https://github.com/revng/orchestra/issues/18
    """
    orchestra("components")


def test_components_json_output_format(orchestra: OrchestraShim, capsys):
    """Checks that `orchestra components --json` produces the expected output format"""
    orchestra("update")
    capsys.readouterr()

    orchestra("components", "--json", "component_A")
    out, err = capsys.readouterr()
    parsed_output = json.loads(out)

    schema = yaml.safe_load(pkg_resources.resource_stream("test.commands", "components_json.schema.yml"))
    jsonschema.validate(parsed_output, schema)
