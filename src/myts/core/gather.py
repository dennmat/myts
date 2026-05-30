from mypy.find_sources import create_source_list
from mypy.modulefinder import BuildSource
from mypy.options import Options


def discover_sources(proj_root: str, options: Options) -> list[BuildSource]:
	"""
	Responsible for returning the list of `BuildSource` objects that Myts will
	use to find type info from.

	Currently we simply rely on mypy's `create_source_list` to gather it for us.
	"""
	sources = create_source_list([proj_root], options=options)
	return sources
