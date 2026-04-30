from functools import lru_cache
import itertools
import os
import pathlib
import sys
from typing import Callable

from mypy import build
from mypy.find_sources import create_source_list
from mypy.nodes import CallExpr, MemberExpr, NameExpr, Statement, StrExpr, TypeInfo, Var
from mypy.options import Options
from mypy.types import (
	AnyType,
	Instance,
	LiteralType,
	TypedDictType,
	UnionType,
	NoneType,
	TypeVarType as MypyTypeVarType,
	get_proper_type,
)

from myts.types import (
	MytsDefType,
	MytsDictType,
	MytsEnumValue,
	MytsExportType,
	MytsField,
	MytsGenericRef,
	MytsListType,
	MytsLiteralValue,
	MytsConfiguration,
	MytsModule,
	MytsPrimitiveType,
	MytsRefType,
	MytsTypeDef,
	MytsTypeExpr,
	MytsTypeParam,
	MytsTypeVar,
	MytsUnionTypeExpr,
)
from myts.utils import is_subclass_of, split_nullable


def extract_mypy_graph(root: pathlib.Path) -> build.BuildResult:
	options = Options()
	options.incremental = False

	if "PYTEST_CURRENT_TEST" in os.environ:  # Ensures import myts. works in tests
		options.mypy_path = ["src"]

	proj_root = str(root.resolve())

	sys.path.insert(0, proj_root)

	sources = create_source_list([proj_root], options=options)

	result = build.build(sources=sources, options=options)

	return result


def extract_type_params(info: TypeInfo) -> list[str]:
	if not info.defn.type_vars:
		return []

	params: list[MytsTypeParam] = []
	for type_var in info.defn.type_vars:
		name = type_var.name

		bound = None
		constraints = None

		if type_var.upper_bound:
			upper_bound = get_proper_type(type_var.upper_bound)
			if not isinstance(upper_bound, AnyType):
				bound = map_type(upper_bound)

		if type_var.values:
			constraints = [
				map_type(get_proper_type(value)) for value in type_var.values
			]

		params.append(MytsTypeParam(name=name, bound=bound, constraints=constraints))

	return params


def has_export_decorator(info: TypeInfo) -> bool:
	if not info.defn.decorators:
		return False

	for decorator in info.defn.decorators:
		if (
			isinstance(decorator, NameExpr) or isinstance(decorator, MemberExpr)
		) and decorator.name == "myts_export":
			return True

	return False


def parse_export_args(call: CallExpr) -> MytsExportType:
	result = MytsExportType.EXPORT

	if call.args:
		arg = call.args[0]

		# @myts_export(False)
		if isinstance(arg, NameExpr):
			if arg.name == "False":
				result = MytsExportType.EXCLUDE

	for name, arg in zip(call.arg_names, call.args):
		if name == "mode":
			if isinstance(arg, StrExpr):
				try:
					value = MytsExportType(arg.value)
				except ValueError:
					# TODO: Should we warn myts_export got an invalid value?
					return None
				else:
					result = value

	return result


def parse_myts_export(info: TypeInfo) -> MytsExportType | None:
	if not info.defn.decorators:
		return None

	for decorator in info.defn.decorators:
		# @myts_export
		if isinstance(decorator, NameExpr) and decorator.name == "myts_export":
			return MytsExportType.EXPORT

		# @myts.myts_export
		if isinstance(decorator, MemberExpr) and decorator.name == "myts_export":
			return MytsExportType.EXPORT

		# @myts_export(...)
		if isinstance(decorator, CallExpr):
			callee = decorator.callee

			if isinstance(callee, NameExpr) and callee.name == "myts_export":
				return parse_export_args(decorator)

			if isinstance(callee, MemberExpr) and callee.name == "myts_export":
				return parse_export_args(decorator)


def map_type(t) -> MytsTypeExpr | None:
	t = get_proper_type(t)

	if isinstance(t, Instance):
		name = t.type.fullname

		if name == "builtins.str" or name == "uuid.UUID" or name == "datetime.datetime":
			return MytsPrimitiveType("str")

		if name == "builtins.int":
			return MytsPrimitiveType("int")

		if name == "builtins.float":
			return MytsPrimitiveType("float")

		if name == "builtins.bool":
			return MytsPrimitiveType("bool")

		if name == "builtins.list":
			return MytsListType(map_type(t.args[0]))

		if name == "builtins.dict":
			return MytsDictType(map_type(t.args[0]), map_type(t.args[1]))

		if t.args:
			return MytsGenericRef(
				t.type.fullname, t.type.name, args=[map_type(arg) for arg in t.args]
			)

		return MytsRefType(name=t.type.name, fq_name=name)

	if isinstance(t, MypyTypeVarType):
		return MytsTypeVar(t.name)

	if isinstance(t, UnionType):
		return MytsUnionTypeExpr([map_type(item) for item in t.items])

	if isinstance(t, NoneType):
		return MytsPrimitiveType("None")

	if isinstance(t, LiteralType):
		return MytsLiteralValue(value=t.value)

	if isinstance(t, TypedDictType):
		return MytsRefType(name=t.fallback.type.name, fq_name=t.fallback.type.fullname)

	return MytsPrimitiveType("any")


def extract_type(
	myts_type: MytsDefType, fq_name: str, node: Statement, module: build.State
) -> MytsTypeDef:
	if myts_type == MytsDefType.ENUM:
		return extract_enum(fq_name, node, module)

	export = parse_myts_export(node)
	is_myts_subclass = is_subclass_of(node, "myts.types.MytsType")

	# myts_export wasn't used, but this is a MytsType inherited obj
	# mark it as a ROOT export
	if export is None and is_myts_subclass:
		export = MytsExportType.ROOT

	bases = []

	for base in node.bases:
		base_type = get_proper_type(base)

		if isinstance(base_type, Instance):
			bases.append(base.type.fullname)

	if node.typeddict_type:
		return extract_typeddict(bases, export, myts_type, fq_name, node, module)

	fields = []
	deps: set[str] = set()

	for name, sym in node.names.items():
		if name.startswith("_"):
			continue

		snode = sym.node

		if not isinstance(snode, Var):
			continue

		if snode.type is None:
			continue

		proper_type = get_proper_type(snode.type)

		nullable = False
		if isinstance(proper_type, MytsUnionTypeExpr):
			proper_type, nullable = split_nullable(proper_type)

		mapped_t = map_type(proper_type)
		fields.append(MytsField(name, mapped_t, nullable))
		deps |= collect_refs(mapped_t)

	return MytsTypeDef(
		type=myts_type,
		export=export,
		name=node.name,
		fq_name=fq_name,
		output_module=module.id,
		bases=bases,
		fields=fields,
		deps=deps,
		type_params=extract_type_params(node),
		enum_values=[],
	)


def extract_typeddict(
	bases: list[str],
	export: MytsExportType,
	myts_type: MytsDefType,
	fq_name: str,
	node: Statement,
	module: build.State,
) -> MytsTypeDef:
	fields = []
	deps: set[str] = set()

	typeddict = node.typeddict_type

	for name, sym in typeddict.items.items():
		if name.startswith("_"):
			continue

		t = get_proper_type(sym)

		nullable = False
		if isinstance(t, MytsUnionTypeExpr):
			t, nullable = split_nullable(t)

		mapped_t = map_type(t)
		fields.append(MytsField(name, mapped_t, nullable))
		deps |= collect_refs(mapped_t)

	output_module = module.id
	type_params = extract_type_params(node)

	typed_dict_def = MytsTypeDef(
		export=export,
		type=myts_type,
		name=node.name,
		bases=bases,
		fq_name=fq_name,
		output_module=output_module,
		fields=fields,
		deps=deps,
		type_params=type_params,
		enum_values=[],
	)

	return typed_dict_def


def extract_enum(fq_name: str, node: Statement, module: build.State) -> MytsTypeDef:
	values: list[MytsEnumValue] = []

	for name, sym in node.names.items():
		if isinstance(sym.node, Var) and sym.node.is_final:
			values.append(MytsEnumValue(name, sym.node.type.last_known_value.value))

	output_module = module.id
	return MytsTypeDef(
		export=MytsExportType.ROOT,
		type=MytsDefType.ENUM,
		name=node.name,
		fq_name=fq_name,
		output_module=output_module,
		bases=[],
		fields=[],
		deps=set(),
		type_params=[],
		enum_values=values,
	)


def parse_myts_type(node: TypeInfo) -> MytsDefType | None:
	if is_subclass_of(node, ("enum.Enum", "enum.IntEnum", "enum.StrEnum")):
		return MytsDefType.ENUM

	elif node.typeddict_type is not None:
		return MytsDefType.OBJECT

	elif is_subclass_of(node, "myts.types.MytsType"):
		return MytsDefType.OBJECT

	return None


def extract_types(build: build.BuildResult) -> dict[str, MytsTypeDef]:
	registry: dict[str, MytsTypeDef] = {}

	for module in build.graph.values():
		if "mypy/typeshed/" in module.path:
			# Using this for now, if somehow this causes conflicts we'll likely
			# want to do a full path comparison
			continue

		if "myts/" in module.path and "/tests/" not in module.path:
			continue

		tree = module.tree

		if not tree:
			continue

		for sym in tree.names.values():
			node = sym.node

			if not isinstance(node, TypeInfo):
				continue

			fq_name = node.fullname

			if fq_name.startswith("myts") and not fq_name.startswith("myts.tests"):
				continue

			myts_type = parse_myts_type(node)

			if myts_type is not None:
				if not fq_name.startswith(module.id):
					# This is likely due to being a reference, we don't want to override
					# this ensures we're only extracting when module and node are the same
					continue
				registry[fq_name] = extract_type(myts_type, fq_name, node, module)

	return registry


def collect_refs(type_expr: MytsTypeExpr) -> set[str]:
	if isinstance(type_expr, MytsGenericRef):
		out = {type_expr.fq_name}
		for arg in type_expr.args:
			out |= collect_refs(arg)
		return out

	if isinstance(type_expr, MytsRefType):
		return {type_expr.fq_name}

	if isinstance(type_expr, MytsListType):
		return collect_refs(type_expr.item)

	if isinstance(type_expr, MytsDictType):
		return collect_refs(type_expr.key) | collect_refs(type_expr.value)

	if isinstance(type_expr, MytsUnionTypeExpr):
		out = set()
		for x in type_expr.options:
			out |= collect_refs(x)
		return out

	return set()


def build_field_collector(
	registry: dict[str, MytsTypeDef],
) -> Callable[[str], tuple[MytsField]]:
	"""
	Returns a method that accepts a fq_name to fetch fields info for.
	Caches on fq_name.
	"""

	@lru_cache(maxsize=None)
	def collect_fields(fq_name: str) -> tuple[MytsField, ...]:
		if fq_name not in registry:
			return ()

		type_def = registry[fq_name]

		field_map: dict[str, MytsField] = {}

		for base in type_def.bases:
			if base not in registry:
				continue

			base_def = registry[base]

			if base_def.export in (MytsExportType.EXCLUDE, MytsExportType.INTERNAL):
				for field in collect_fields(base):
					field_map[field.name] = field

		for field in type_def.fields:
			field_map[field.name] = field

		return tuple(field_map.values())

	return collect_fields


def resolve_dependencies(
	roots: list[MytsTypeDef], registry: dict[str, MytsTypeDef]
) -> dict[str, MytsTypeDef]:
	visited: set[str] = set()
	result: dict[str, MytsTypeDef] = {}

	def visit(fq_name: str):
		if fq_name in visited:
			return

		visited.add(fq_name)

		if fq_name not in registry:
			return

		t = registry[fq_name]
		result[fq_name] = t

		for dep in t.deps:
			visit(dep)

	for root in roots:
		visit(root.fq_name)

	return result


def topological_sort(types: dict[str, MytsTypeDef]) -> list[MytsTypeDef]:
	visited: set[str] = set()
	out: list[MytsTypeDef] = []

	def visit(t):
		if t.fq_name in visited:
			return

		visited.add(t.fq_name)

		for dep in t.deps:
			if dep in types:
				visit(types[dep])

		out.append(t)

	for t in types.values():
		visit(t)

	return out


def collect_imports(type_defs: list[MytsTypeDef], registry: dict[str, MytsTypeDef]):
	imports: dict[str, set[str]] = {}  # module -> TypeDef names

	for type_def in type_defs:
		for dep in itertools.chain(type_def.deps, type_def.bases):
			if dep not in registry:
				continue

			dep_type = registry[dep]

			# Only include if the type is exportable
			# most likely scenarios are excluded "MytsType" inherited utility classes
			if dep_type.export in (MytsExportType.EXCLUDE, MytsExportType.INTERNAL):
				continue

			if dep_type.output_module == type_def.output_module:
				continue

			imports.setdefault(dep_type.output_module, set()).add(dep_type.name)

	return imports


def extract_modules(
	config: MytsConfiguration,
) -> tuple[dict[str, MytsTypeDef], dict[str, MytsModule]]:
	build = extract_mypy_graph(config.root)

	registry = extract_types(build)

	roots = [
		t
		for t in registry.values()
		if t.export in (MytsExportType.ROOT, MytsExportType.EXPORT)
	]

	shooken = resolve_dependencies(roots, registry)

	topologically_sorted = topological_sort(shooken)

	modules: dict[str, MytsModule] = {}
	for t in topologically_sorted:
		if t.output_module in modules:
			output_module = modules[t.output_module]
		else:
			output_module = MytsModule(name=t.output_module, type_defs=[], imports={})
			modules[t.output_module] = output_module

		output_module.type_defs.append(t)

	for output_module in modules.values():
		output_module.imports = collect_imports(output_module.type_defs, shooken)

	return registry, modules
