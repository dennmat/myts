from functools import lru_cache
import sys
from typing import Callable

from mypy import build
from mypy.build import BuildResult
from mypy.options import Options

from myts.config import MytsConfiguration
from myts.core.ast import ASTContext
from myts.core.bundle import distill_modules
from myts.core.extract import extract_ir
from myts.core.gather import discover_sources
from myts.core.ir import (
	ExportType,
	Field,
	TypeDef,
)
from myts.core.types import AnalysisResult


class Analyzer:
	build: BuildResult
	ast: ASTContext

	config: MytsConfiguration
	root_module: str

	def __init__(
		self, build_result: BuildResult, ast_ctx: ASTContext, config: MytsConfiguration
	):
		self.build = build_result
		self.ast = ast_ctx
		self.config = config
		self.root_module = (
			config.root.name
		)  # If root has a __init__ this will work, TODO handle the error otherwise

	def analyze(self) -> AnalysisResult:
		roots, registry = extract_ir(self.root_module, self.build, self.ast)
		modules = distill_modules(roots, registry)

		return AnalysisResult(
			modules=modules,
			registry=registry,
		)


def build_field_collector(
	registry: dict[str, TypeDef],
) -> Callable[[str], tuple[Field]]:
	"""
	Returns a method that accepts a fullname to fetch fields info for.
	Caches on fullname.
	"""

	@lru_cache(maxsize=None)
	def collect_fields(fullname: str) -> tuple[Field, ...]:
		if fullname not in registry:
			return ()

		type_def = registry[fullname]

		field_map: dict[str, Field] = {}

		for base in type_def.bases:
			if base not in registry:
				continue

			base_def = registry[base]

			if base_def.export != ExportType.EXCLUDE:
				for field in collect_fields(base):
					field_map[field.name] = field

		for field in type_def.fields:
			field_map[field.name] = field

		return tuple(field_map.values())

	return collect_fields


def create_analyzer(config: MytsConfiguration) -> Analyzer:
	proj_root = str(config.root.resolve())
	sys.path.insert(0, proj_root)

	options = Options()
	options.incremental = False
	options.follow_imports = "normal"
	options.ignore_errors = False

	sources = discover_sources(proj_root, options)

	build_result = build.build(sources=sources, options=options)

	if len(build_result.errors) > 0:
		# TODO Print nicelier
		print(build_result.errors)

	ast_ctx = ASTContext(sources, options)

	analyzer = Analyzer(build_result, ast_ctx, config)

	return analyzer
