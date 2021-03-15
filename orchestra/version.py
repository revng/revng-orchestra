from pkg_resources import get_distribution

__version__ = get_distribution("orchestra").version
__parsed_version__ = get_distribution("orchestra").parsed_version
