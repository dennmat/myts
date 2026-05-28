import copy
from functools import lru_cache
import itertools
import sys
from typing import Callable

from mypy import build
from mypy.build import State
from mypy.find_sources import create_source_list
from mypy.modulefinder import BuildSource
from mypy.nodes import (
	AssignmentStmt,
	CallExpr,
	ClassDef,
	Expression,
	IntExpr,
	MemberExpr,
	MypyFile,
	NameExpr,
	StrExpr,
	TypeAliasStmt,
	TypeInfo,
	Var,
	TypeAlias,
)
from mypy.options import Options
from mypy.types import (
	Type,
	AnyType,
	Instance,
	LiteralType,
	NoneType,
	TypeVarType,
	TypedDictType,
	UnionType,
	get_proper_type,
	TypeAliasType,
)

from myts.config import MytsConfiguration
from myts.core.ast import ASTContext
from myts.core.build import BuildContext
from myts.core.ir import (
	AliasDef,
	AliasRef,
	DictType,
	EnumDef,
	EnumValue,
	ExportType,
	Field,
	FieldSource,
	GenericRef,
	ListType,
	LiteralValue,
	Module,
	PrimitiveType,
	RefType,
	SymbolEntry,
	SymbolKind,
	TypeDef,
	TypeExpr,
	TypeParam,
	TypeVar,
	TypedDictDef,
	ClassDef as MytsClassDef,
	UnionTypeExpr,
)
from myts.core.types import AnalysisResult
from myts.utils.mypy import is_enum, is_subclass_of, is_typeddict


def topological_sort(types: dict[str, TypeDef]) -> list[TypeDef]:
	visited: set[str] = set()
	out: list[TypeDef] = []

	def visit(t):
		if t.fullname in visited:
			return

		visited.add(t.fullname)

		for dep in t.deps:
			if dep in types:
				visit(types[dep])

		out.append(t)

	for t in types.values():
		visit(t)

	return out


def resolve_dependencies(
	roots: list[TypeDef], registry: dict[str, TypeDef]
) -> dict[str, TypeDef]:
	visited: set[str] = set()
	result: dict[str, TypeDef] = {}

	def visit(fullname: str):
		if fullname in visited:
			return

		visited.add(fullname)

		if fullname not in registry:
			return

		t = registry[fullname]
		result[fullname] = t

		for dep in t.deps:
			visit(dep)

	for root in roots:
		visit(root.fullname)

	return result


def collect_imports(type_defs: list[TypeDef], registry: dict[str, TypeDef]):
	imports: dict[str, set[str]] = {}  # module -> TypeDef names

	for type_def in type_defs:
		if not hasattr(type_def, "bases"):
			continue

		for dep in itertools.chain(type_def.deps, type_def.bases):
			if dep not in registry:
				continue

			dep_type = registry[dep]

			# Only include if the type is exportable
			# most likely scenarios are excluded "MytsType" inherited utility classes
			if dep_type.export in (ExportType.EXCLUDE,):
				continue

			if dep_type.output_module == type_def.output_module:
				continue

			imports.setdefault(dep_type.output_module, set()).add(dep_type.name)

	return imports


def collect_refs(type_expr: TypeExpr) -> set[str]:
	if isinstance(type_expr, GenericRef):
		out = {type_expr.fullname}
		for arg in type_expr.args:
			out |= collect_refs(arg)
		return out

	if isinstance(type_expr, AliasRef):
		out = {type_expr.fullname}
		for arg in type_expr.args:
			out |= collect_refs(arg)
		return out

	if isinstance(type_expr, RefType):
		return {type_expr.fullname}

	if isinstance(type_expr, ListType):
		return collect_refs(type_expr.item)

	if isinstance(type_expr, DictType):
		return collect_refs(type_expr.key) | collect_refs(type_expr.value)

	if isinstance(type_expr, UnionTypeExpr):
		out = set()
		for x in type_expr.options:
			out |= collect_refs(x)
		return out

	return set()


class Analyzer:
	build: BuildContext
	ast: ASTContext

	config: MytsConfiguration
	root_module: str

	parsed_file_cache: dict[int, MypyFile]

	# Pass 1 fills this `analyze_symbols`
	symbol_registry: dict[str, SymbolEntry]

	# Pass 2 fills these `extract_ir`
	roots: set[str]
	typedef_registry: dict[str, TypeDef]

	modules: dict[str, Module]

	def __init__(
		self, build_ctx: BuildContext, ast_ctx: ASTContext, config: MytsConfiguration
	):
		self.build = build_ctx
		self.ast = ast_ctx
		self.config = config
		self.root_module = (
			config.root.name
		)  # If root has a __init__ this will work, TODO handle the error otherwise

		self.parsed_file_cache = {}

		self.symbol_registry = {}
		self.roots = set()
		self.typedef_registry = {}
		self.modules = {}

	def analyze(self) -> AnalysisResult:
		self.analyze_symbols()
		self.extract_ir()
		self.distill_modules()

		return AnalysisResult(
			modules=copy.deepcopy(self.modules),
			registry=copy.deepcopy(self.typedef_registry),
		)

	def analyze_symbols(self):
		for source in self.ast.sources:
			tree = self.get_ast_tree_for_source(source)

			for node in tree.defs:
				if isinstance(node, ClassDef):
					fullname = f"{source.module}.{node.name}"
					info = self.build.get_typeinfo(fullname)
					export = self.parse_myts_export(info)

					if export is None:
						export = ExportType.AUTO

					kind: SymbolKind
					if is_enum(info):
						kind = SymbolKind.ENUM
					elif is_typeddict(info):
						kind = SymbolKind.TYPED_DICT
					else:
						kind = SymbolKind.CLASS

					self.symbol_registry[fullname] = SymbolEntry(
						fullname=fullname, kind=kind, export=export
					)

				elif isinstance(node, TypeAliasStmt):
					semantic_tree = self.build.result.graph[source.module].tree

					sym = semantic_tree.names.get(node.name.name)
					if not sym:
						return None

					if not isinstance(sym.node, TypeAlias):
						return None

					alias = sym.node
					self.symbol_registry[alias.fullname] = SymbolEntry(
						fullname=alias.fullname,
						kind=SymbolKind.TYPE_ALIAS,
						export=ExportType.AUTO,
					)

	def extract_ir(self):
		roots: list[str] = []
		registry: dict[str, TypeDef] = {}

		for state in self.build.result.graph.values():
			tree = getattr(state, "tree", None)
			if tree is None:
				continue

			types, source_roots = self.analyze_state(state)

			roots += source_roots

			for typ in types:
				registry[typ.fullname] = typ

		self.roots = roots
		self.typedef_registry = registry

	def distill_modules(self):
		resolved = resolve_dependencies(self.roots, self.typedef_registry)

		topologically_sorted = topological_sort(resolved)

		modules: dict[str, Module] = {}

		for type_def in topologically_sorted:
			if type_def.output_module in modules:
				output_module = modules[type_def.output_module]
			else:
				output_module = Module(
					fullname=type_def.output_module, registry={}, imports={}
				)
				modules[type_def.output_module] = output_module

			output_module.registry[type_def.fullname] = type_def

		for output_module in modules.values():
			output_module.imports = collect_imports(
				output_module.registry.values(), resolved
			)

		self.modules = modules

	def get_ast_tree_for_source(self, source: BuildSource) -> MypyFile:
		source_id = id(source)

		if source_id in self.parsed_file_cache:
			return self.parsed_file_cache[source_id]

		self.parsed_file_cache[source_id] = self.ast.parse(source)
		return self.parsed_file_cache[source_id]

	def analyze_state(self, state: State) -> tuple[list[TypeDef], list[TypeDef]]:
		tree = state.tree
		results: list[TypeDef] = []
		roots: list[TypeDef] = []

		def is_root_export(type_def: TypeDef) -> bool:
			return type_def.is_entrypoint or type_def.export == ExportType.FORCE_EXPORT

		for sym in tree.names.values():
			node = sym.node

			if not node.fullname.startswith(self.root_module + "."):
				continue

			if isinstance(node, TypeInfo):
				type_def = self.extract(node.fullname, node)
				if type_def:
					if is_root_export(type_def):
						roots.append(type_def)
					results.append(type_def)
			elif isinstance(node, TypeAlias):
				mapped_t = self.map_type(node.target)
				deps = collect_refs(mapped_t)

				alias_def = AliasDef(
					fullname=node.fullname,
					name=node.name,
					deps=deps,
					export=ExportType.AUTO,
					target=mapped_t,
					is_entrypoint=False,
					type_params=self.extract_alias_type_params(node),
				)

				self.symbol_registry[node.fullname] = alias_def
				results.append(alias_def)

		return results, roots

	def parse_export_args(self, call: CallExpr) -> ExportType:
		result = ExportType.AUTO

		if call.args:
			arg = call.args[0]

			# @myts_export(False)
			if isinstance(arg, NameExpr):
				if arg.name == "False":
					result = ExportType.EXCLUDE

		for name, arg in zip(call.arg_names, call.args):
			if name == "mode":
				if isinstance(arg, StrExpr):
					try:
						value = ExportType(arg.value)
					except ValueError:
						# TODO: Should we warn myts_export got an invalid value?
						return None
					else:
						result = value

		return result

	def parse_myts_export(self, info: TypeInfo) -> ExportType | None:
		if not info.defn.decorators:
			return None

		for decorator in info.defn.decorators:
			# @myts_export
			if isinstance(decorator, NameExpr) and decorator.name == "myts_export":
				return ExportType.EXPORT

			# @myts.myts_export
			if isinstance(decorator, MemberExpr) and decorator.name == "myts_export":
				return ExportType.EXPORT

			# @myts_export(...)
			if isinstance(decorator, CallExpr):
				callee = decorator.callee

				if isinstance(callee, NameExpr) and callee.name == "myts_export":
					return self.parse_export_args(decorator)

				if isinstance(callee, MemberExpr) and callee.name == "myts_export":
					return self.parse_export_args(decorator)

	def extract_type_params(self, info: TypeInfo) -> list[TypeParam]:
		if not info.defn.type_vars:
			return []

		params: list[TypeParam] = []
		for type_var in info.defn.type_vars:
			name = type_var.name

			bound = None
			constraints = None

			if type_var.upper_bound:
				upper_bound = get_proper_type(type_var.upper_bound)

				if not isinstance(upper_bound, AnyType) and not (
					isinstance(upper_bound, Instance)
					and upper_bound.type.fullname == "builtins.object"
				):
					bound = self.type(upper_bound)

			if hasattr(type_var, "values") and type_var.values:
				constraints = [self.map_type(value) for value in type_var.values]

			params.append(TypeParam(name=name, bound=bound, constraints=constraints))

		return params

	def extract_alias_type_params(self, info: TypeAlias) -> list[TypeParam]:
		if not info.alias_tvars:
			return []

		params: list[TypeParam] = []
		for type_var in info.alias_tvars:
			name = type_var.name

			bound = None
			constraints = None

			if type_var.upper_bound:
				upper_bound = get_proper_type(type_var.upper_bound)

				if not isinstance(upper_bound, AnyType) and not (
					isinstance(upper_bound, Instance)
					and upper_bound.type.fullname == "builtins.object"
				):
					bound = self.type(upper_bound)

			if hasattr(type_var, "values") and type_var.values:
				constraints = [self.map_type(value) for value in type_var.values]

			params.append(TypeParam(name=name, bound=bound, constraints=constraints))

		return params

	def extract_enum_value(self, sym: Var, stmt: AssignmentStmt) -> int | str | None:
		# 1. Preferred: mypy resolved value
		final_value = getattr(sym, "final_value", None)
		if isinstance(final_value, (int, str)):
			return final_value

		# 2. Fallback: inspect RHS AST
		rvalue: Expression = stmt.rvalue

		# literal int
		if isinstance(rvalue, IntExpr):
			return rvalue.value

		# literal string
		if isinstance(rvalue, StrExpr):
			return rvalue.value

		# 3. Simple reference (e.g. B = A)
		if isinstance(rvalue, NameExpr):
			# might point to another enum member
			node = rvalue.node
			if isinstance(node, Var):
				ref_val = getattr(node, "final_value", None)
				if isinstance(ref_val, (int, str)):
					return ref_val

		# 4. Member access (rare but possible)
		if isinstance(rvalue, MemberExpr):
			node = rvalue.node
			if isinstance(node, Var):
				ref_val = getattr(node, "final_value", None)
				if isinstance(ref_val, (int, str)):
					return ref_val

		# 5. auto() or function calls → unresolved
		if isinstance(rvalue, CallExpr):
			return None

		return None

	def extract_enum(self, fullname: str, info: TypeInfo) -> EnumDef:
		export = self.parse_myts_export(info)

		if export is None:
			export = ExportType.AUTO

		values: list[EnumValue] = []

		for name in info.names.keys():
			stmt = self.ast.cache.get((fullname, name))

			if not isinstance(stmt, AssignmentStmt):
				continue

			if len(stmt.lvalues) != 1:
				continue

			lvalue = stmt.lvalues[0]

			if not isinstance(lvalue, NameExpr):
				continue

			name = lvalue.name

			sym = info.names.get(name)
			if sym is None:
				continue

			if not isinstance(sym.node, Var):
				continue

			values.append(EnumValue(name, self.extract_enum_value(sym.node, stmt)))

		return EnumDef(
			name=info.name,
			fullname=fullname,
			deps=set(),
			export=export,
			is_entrypoint=False,
			values=values,
		)

	def collect_fields(self, info: TypeInfo) -> list[FieldSource]:
		fields = []

		for name, sym in info.names.items():
			if not isinstance(sym.node, Var):
				continue

			var = sym.node

			ast_match = self.ast.cache.get((info.fullname, var.name))

			fields.append(
				FieldSource(
					fullname=info.fullname,
					name=var.name,
					annotation=ast_match.type if ast_match else None,
					resolved=var.type,
					var=var,
				)
			)

		return fields

	def extract_class(self, fullname: str, info: TypeInfo) -> MytsClassDef:
		export = self.parse_myts_export(info)
		is_myts_subclass = is_subclass_of(info, "myts.core.types.MytsType")

		if export is None:
			export = ExportType.AUTO

		bases = []

		for base in info.bases:
			base_type = get_proper_type(base)

			if isinstance(base_type, Instance):
				if base.type.fullname.startswith(self.root_module + "."):
					bases.append(base.type.fullname)

		fields = []
		deps: set[str] = set()

		collected_fields = self.collect_fields(info)

		for field in collected_fields:
			if field.name.startswith("_"):
				continue

			snode = field.var

			if snode.type is None:
				continue

			# proper_type = get_proper_type(snode.type)

			nullable = False
			# if isinstance(proper_type, UnionTypeExpr):
			# proper_type, nullable = split_nullable(proper_type)

			mapped_t = self.map_type(snode.type)

			# mapped_t = self.map_annotation(field.annotation, proper_type)
			fields.append(Field(field.name, mapped_t, nullable))
			deps |= collect_refs(mapped_t)

		return MytsClassDef(
			export=export,
			name=info.name,
			fullname=fullname,
			bases=bases,
			fields=fields,
			deps=deps,
			type_params=self.extract_type_params(info),
			is_entrypoint=is_myts_subclass,
		)

	def extract_typeddict(self, fullname: str, info: TypeInfo) -> TypedDictDef:
		export = self.parse_myts_export(info)
		is_myts_subclass = is_subclass_of(info, "myts.core.types.MytsType")

		if export is None:
			export = ExportType.AUTO

		bases = []

		for base in info.bases:
			base_type = get_proper_type(base)

			if isinstance(base_type, Instance):
				if base.type.fullname.startswith(self.root_module + "."):
					bases.append(base.type.fullname)

		fields = []
		deps: set[str] = set()

		typeddict = info.typeddict_type

		for name, sym in typeddict.items.items():
			if name.startswith("_"):
				continue

			"""t = get_proper_type(sym)

			nullable = False
			if isinstance(t, UnionTypeExpr):
				t, nullable = split_nullable(t)
			"""

			mapped_t = self.map_type(sym)
			fields.append(Field(name, mapped_t, False))
			deps |= collect_refs(mapped_t)

		return MytsClassDef(
			export=export,
			name=info.name,
			fullname=fullname,
			bases=bases,
			fields=fields,
			deps=deps,
			is_entrypoint=is_myts_subclass,
			type_params=self.extract_type_params(info),
		)

	def extract(self, fullname: str, info: TypeInfo) -> TypeDef:
		if is_enum(info):
			return self.extract_enum(fullname, info)

		if is_typeddict(info):
			return self.extract_typeddict(fullname, info)

		return self.extract_class(fullname, info)

	def map_type(self, info: Type) -> TypeExpr:
		if isinstance(info, TypeAliasType):
			fullname = info.alias.fullname
			if fullname in self.symbol_registry and isinstance(
				self.symbol_registry[fullname], AliasDef
			):
				if len(info.args) > 0:
					args = [self.map_type(i) for i in info.args]
				else:
					args = []

				return AliasRef(
					short_name=info.alias.name, fullname=fullname, args=args
				)

		return self.map_semantic_type(info)

	def map_semantic_type(self, semantic_type: Type) -> TypeExpr:
		semantic_type = get_proper_type(semantic_type)

		if isinstance(semantic_type, Instance):
			fullname = semantic_type.type.fullname

			if (
				fullname == "builtins.str"
				or fullname == "uuid.UUID"
				or fullname == "datetime.datetime"
			):
				return PrimitiveType("str")

			if fullname == "builtins.int":
				return PrimitiveType("int")

			if fullname == "builtins.float":
				return PrimitiveType("float")

			if fullname == "builtins.bool":
				return PrimitiveType("bool")

			if fullname == "builtins.list":
				return ListType(self.map_type(semantic_type.args[0]))

			if fullname == "builtins.dict":
				return DictType(
					self.map_type(semantic_type.args[0]),
					self.map_type(semantic_type.args[1]),
				)

			if not fullname.startswith(self.root_module):
				return PrimitiveType("any")

			if semantic_type.args:
				return GenericRef(
					fullname,
					semantic_type.type.name,
					args=[self.map_type(i) for i in semantic_type.args],
				)

			return RefType(name=semantic_type.type.name, fullname=fullname)

		if isinstance(semantic_type, TypeVarType):
			return TypeVar(semantic_type.name)

		if isinstance(semantic_type, UnionType):
			return UnionTypeExpr([self.map_type(i) for i in semantic_type.items])

		if isinstance(semantic_type, NoneType):
			return PrimitiveType("None")

		if isinstance(semantic_type, LiteralType):
			return LiteralValue(value=semantic_type.value)

		if isinstance(semantic_type, TypedDictType):
			return RefType(
				name=semantic_type.fallback.type.name,
				fullname=semantic_type.fallback.type.fullname,
			)

		return PrimitiveType("any")


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


def discover_sources(proj_root: str, options: Options) -> list[BuildSource]:
	sources = create_source_list([proj_root], options=options)
	return sources


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

	build_ctx = BuildContext(build_result)
	ast_ctx = ASTContext(sources, options)

	analyzer = Analyzer(build_ctx, ast_ctx, config)

	return analyzer
