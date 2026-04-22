import pathlib
import sys

from mypy import build
from mypy.find_sources import create_source_list
from mypy.nodes import MemberExpr, NameExpr, Statement, TypeInfo, Var
from mypy.options import Options
from mypy.types import (
	Instance,
	LiteralType,
	TypedDictType,
	UnionType,
	NoneType,
	TypeVarType as MypyTypeVarType,
	get_proper_type,
)

from myts.types import (
	MytsDictType,
	MytsEnumDef,
	MytsEnumValue,
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
	MytsTypeVar,
	MytsTypedDictDef,
	MytsUnionTypeExpr,
	MytsClassDef,
)
from myts.utils import detect_enum_kind, is_subclass_of, split_nullable


def should_export(class_def: TypeInfo) -> bool:
	return is_subclass_of(class_def, "myts.types.MytsType")


def extract_mypy_graph(root: pathlib.Path) -> build.BuildResult:
	options = Options()
	options.incremental = False

	proj_root = str(root.resolve())

	sys.path.insert(0, proj_root)

	sources = create_source_list([proj_root], options=options)

	result = build.build(sources=sources, options=options)

	return result


def get_type_params(info) -> list[str]:
	if not info.defn.type_vars:
		return []

	return [tv for tv in info.defn.type_vars]


def has_export_decorator(info) -> bool:
	if not info.defn.decorators:
		return False

	for dec in info.defn.decorators:
		if isinstance(dec, NameExpr) and dec.name == "myts_export":
			return True

		if isinstance(dec, MemberExpr) and dec.name == "myts_export":
			return True

	return False


def map_type(t) -> MytsTypeExpr | None:
	t = get_proper_type(t)

	if isinstance(t, Instance):
		name = t.type.fullname

		if (
			name == "builtins.str" or name == "uuid.UUID"
		):  # or name == "datetime.datetime"?:
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
		if is_subclass_of(t.fallback.type, "enum.Enum"):
			...
			# What we want is to add the referenced enum as a dependency
			# so it gets included
			# then we want to output it as it is effectively so likle MyEnum.THIS | that | this
			# this naive implementation outputs "THIS" | ...
			# return LiteralValueType()
		return MytsLiteralValue(value=t.value)

	if isinstance(t, TypedDictType):
		return MytsRefType(name=t.fallback.type.name, fq_name=t.fallback.type.fullname)

	return MytsPrimitiveType("any")


def extract_class(fq_name: str, node: Statement, module: build.State) -> MytsClassDef:
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

		t = get_proper_type(snode.type)

		nullable = False
		if isinstance(t, MytsUnionTypeExpr):
			t, nullable = split_nullable(t)

		mapped_t = map_type(t)
		fields.append(MytsField(name, mapped_t, nullable))
		deps |= collect_refs(mapped_t)

	output_module = module.id
	return MytsClassDef(
		node.name,
		fq_name,
		output_module,
		fields,
		deps,
		get_type_params(node),
		is_exported=True,
	)


def extract_typeddict(
	fq_name: str, node: Statement, module: build.State
) -> MytsTypedDictDef:
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
	type_params = get_type_params(node)

	typed_dict_def = MytsTypedDictDef(
		node.name,
		fq_name,
		output_module,
		fields,
		deps,
		type_params,
		is_exported=has_export_decorator(node),
	)  # Once decorators are implemented is_exported will need to be changed, this determines if its auto exported vs only exported if referenced

	return typed_dict_def


def extract_enum(fq_name: str, node: Statement, module: build.State) -> MytsEnumDef:
	values: list[MytsEnumValue] = []

	for name, sym in node.names.items():
		if isinstance(sym.node, Var) and sym.node.is_final:
			values.append(MytsEnumValue(name, sym.node.type.last_known_value.value))

	enum_kind = detect_enum_kind(values)

	output_module = module.id
	return MytsEnumDef(
		enum_kind,
		node.name,
		fq_name,
		output_module,
		values,
		{},
		[],
		is_exported=has_export_decorator(node),
	)  # Once decorators are implemented is_exported bla bla see above


def extract_types(build: build.BuildResult) -> dict[str, MytsTypeDef]:
	registry: dict[str, MytsTypeDef] = {}

	for module in build.graph.values():
		if "mypy/typeshed/" in module.path:  # Might be a better way than this
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

			if is_subclass_of(node, ("enum.Enum", "enum.IntEnum", "enum.StrEnum")):
				registry[fq_name] = extract_enum(fq_name, node, module)

			elif node.typeddict_type is not None:
				registry[fq_name] = extract_typeddict(fq_name, node, module)

			elif should_export(node):
				registry[fq_name] = extract_class(fq_name, node, module)

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


def collect_imports(type_defs: list[MytsTypeDef], all_types: dict[str, MytsTypeDef]):
	imports: dict[str, set[str]] = {}  # module -> TypeDef names

	for t in type_defs:
		for dep in t.deps:
			if dep not in all_types:
				continue

			dep_type = all_types[dep]

			if dep_type.output_module == t.output_module:
				continue

			imports.setdefault(dep_type.output_module, set()).add(dep_type.name)

	return imports


def extract_modules(config: MytsConfiguration) -> dict[str, MytsModule]:
	build = extract_mypy_graph(config.root)

	registry = extract_types(build)

	roots = [t for t in registry.values() if t.is_exported]

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

	return modules
