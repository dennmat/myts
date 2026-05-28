from ast import expr

from mypy.errors import Errors
from mypy.modulefinder import BuildSource
from mypy.nodes import AssignmentStmt, ClassDef, MypyFile, TypeAliasStmt
from mypy.options import Options
from mypy.parse import parse

type ASTCache = dict[tuple[str, str], AssignmentStmt | TypeAliasStmt | expr]


class ASTContext:
	sources: list[BuildSource]
	options: Options
	errors: Errors
	cache: ASTCache

	def __init__(self, sources: list[BuildSource], options: Options):
		self.sources = sources
		self.options = options

		self.errors = Errors(self.options)

		self.cache = {}

		self.build_cache()

	def build_cache(self):
		for source in self.sources:
			parsed = self.parse(source)

			# tree = parsed.tree
			for node in parsed.defs:
				if isinstance(node, ClassDef):
					fullname = f"{source.module}.{node.name}"
					for stmt in node.defs.body:
						if isinstance(stmt, AssignmentStmt):
							self.cache[(fullname, stmt.lvalues[0].name)] = (
								stmt  # TODO make sure lvalue is len == 1 and is NameExpr
							)

	def parse(self, source: BuildSource) -> MypyFile:
		with open(source.path) as f:
			return parse(
				f.read(),
				fnam=source.path,
				module=source.module,
				errors=self.errors,
				options=self.options,
				file_exists=True,
				eager=True,
			)
