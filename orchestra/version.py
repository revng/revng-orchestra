from pathlib import Path
from packaging.version import parse as parse_version

version_file = Path(__file__).parent / "support/VERSION"

__version__ = version_file.read_text().strip()
__parsed_version__ = parse_version(__version__)
