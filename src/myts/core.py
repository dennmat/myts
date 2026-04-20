from collections import defaultdict
import pathlib
import sys
from typing import Literal, TypeAliasType

from mypy import build, modulefinder
from mypy.find_sources import create_source_list
from mypy.nodes import MemberExpr, NameExpr, Statement, TypeInfo, Var
from mypy.options import Options
from mypy.types import (
	Instance, LiteralType, TypedDictType, UnionType, NoneType, TypeVarType as MypyTypeVarType, get_proper_type
)

from myts.extractors.ts import convert_ir_to_ts_ir
from myts.types import (
	DictType, EnumDef, EnumValue, Field, GenericRef, ListType, LiteralValueType, MytsConfiguration, OutputModule, PrimitiveType, 
	RefType, TypeDef, TypeExpr, TypeVarType, TypedDictDef, UnionTypeExpr, ClassDef
)
from myts.utils import detect_enum_kind, is_subclass_of, split_nullable


def should_export(class_def: TypeInfo) -> bool:
	return is_subclass_of(class_def, "myts.types.MytsType")

def extract_mypy_graph(root: pathlib.Path) -> build.BuildResult:
	options = Options()
	options.incremental = False

	proj_root = str(root.resolve())

	sys.path.insert(0, proj_root)

	sources = create_source_list(
		[proj_root],
		options=options
	)
	
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

def map_type(t) -> TypeExpr | None:
	t = get_proper_type(t)
	
	if isinstance(t, Instance):
		name = t.type.fullname

		if name == "builtins.str" or name == "uuid.UUID": # or name == "datetime.datetime"?:
			return PrimitiveType("str")
		
		if name == "builtins.int":
			return PrimitiveType("int")

		if name == "builtins.float":
			return PrimitiveType("float")

		if name == "builtins.bool":
			return PrimitiveType("bool")
		
		if name == "builtins.list":
			return ListType(map_type(t.args[0]))
		
		if name == "builtins.dict":
			return DictType(
				map_type(t.args[0]),
				map_type(t.args[1])
			)
		
		if t.args:
			return GenericRef(t.type.fullname, t.type.name, args=[map_type(arg) for arg in t.args])
		
		return RefType(name=t.type.name, fq_name=name)
	
	if isinstance(t, MypyTypeVarType):
		return TypeVarType(t.name)

	if isinstance(t, UnionType):
		return UnionTypeExpr([map_type(item) for item in t.items])

	if isinstance(t, NoneType):
		return PrimitiveType("None")

	if isinstance(t, LiteralType):
		if (is_subclass_of(t.fallback.type, "enum.Enum")):
			print("T val", t.value, t.value.__class__, t.fallback.type.names[t.value])
			# COMPLEX WHAT WE WANT IS TO ADD THE REFERENCED ENUM AS A "DEPENDENCY"
			#	so it gets included
			# then we want to output it as it is effectively so likle MyEnum.THIS | that | this
			#	this naive implementation outputs "THIS" | ...
			#return LiteralValueType()
		return LiteralValueType(value=t.value)
	
	if isinstance(t, TypedDictType):
		return RefType(name=t.fallback.type.name, fq_name=t.fallback.type.fullname)

	return PrimitiveType("any")


def extract_class(fq_name: str, node: Statement, module: build.State) -> ClassDef:
	fields = []
	deps: set[str] = set()

	for name, sym in node.names.items():
		if name.startswith('_'):
			continue
		
		snode = sym.node

		if not isinstance(snode, Var):
			continue

		if snode.type is None:
			continue

		t = get_proper_type(snode.type)

		nullable = False
		if isinstance(t, UnionTypeExpr):
			t, nullable = split_nullable(t)
		
		mapped_t = map_type(t)
		fields.append(Field(name, mapped_t, nullable))
		deps |= collect_refs(mapped_t)

	output_module = module.id
	return ClassDef(node.name, fq_name, output_module, fields, deps, get_type_params(node), is_exported=True)


def extract_typeddict(fq_name: str, node: Statement, module: build.State) -> TypedDictDef:
	fields = []
	deps: set[str] = set()

	typeddict = node.typeddict_type

	for name, sym in typeddict.items.items():
		if name.startswith('_'):
			continue

		t = get_proper_type(sym)

		nullable = False
		if isinstance(t, UnionTypeExpr):
			t, nullable = split_nullable(t)
		
		mapped_t = map_type(t)
		fields.append(Field(name, mapped_t, nullable))
		deps |= collect_refs(mapped_t)
	
	output_module = module.id
	type_params = get_type_params(node)

	typed_dict_def = TypedDictDef(node.name, fq_name, output_module, fields, deps, type_params, is_exported=has_export_decorator(node)) # Once decorators are implemented is_exported will need to be changed, this determines if its auto exported vs only exported if referenced

	if len(type_params) > 0:
		return instantiate_generic(typed_dict_def, )

	return typed_dict_def


def extract_enum(fq_name: str, node: Statement, module: build.State) -> EnumDef:
	values: list[EnumValue] = []

	for name, sym in node.names.items():
		if isinstance(sym.node, Var) and sym.node.is_final:
			values.append(EnumValue(name, sym.node.type.last_known_value.value))
	
	enum_kind = detect_enum_kind(values)
	
	output_module = module.id
	return EnumDef(enum_kind, node.name, fq_name, output_module, values, {}, [], is_exported=has_export_decorator(node)) # Once decorators are implemented is_exported bla bla see above


def extract_types(build: build.BuildResult) -> dict[str, TypeDef]:
	registry: dict[str, TypeDef] = {}

	for module in build.graph.values():
		if 'mypy/typeshed/' in module.path: # Might be a better way than this
			continue

		if 'myts/' in module.path and '/tests/' not in module.path:
			continue
		
		tree = module.tree

		if not tree:
			continue

		for _, sym in tree.names.items():
			node = sym.node

			if not isinstance(node, TypeInfo):
				continue

			fq_name = node.fullname

			if fq_name.startswith('myts') and not fq_name.startswith('myts.tests'):
				continue
			
			if is_subclass_of(node, ("enum.Enum", "enum.IntEnum", "enum.StrEnum")):
				registry[fq_name] = extract_enum(fq_name, node, module)

			elif node.typeddict_type is not None:
				registry[fq_name] = extract_typeddict(fq_name, node, module)
			
			elif should_export(node):
				registry[fq_name] = extract_class(fq_name, node, module)
	
	return registry


def collect_refs(type_expr: TypeExpr) -> set[str]:
	if isinstance(type_expr, GenericRef):
		out = {type_expr.fq_name}
		for arg in type_expr.args:
			out |= collect_refs(arg)
		return out

	if isinstance(type_expr, RefType):
		return {type_expr.fq_name}
	
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


def resolve_dependencies(roots: list[TypeDef], registry: dict[str, TypeDef]) -> dict[str, TypeDef]:
	visited: set[str] = set()
	result: dict[str, TypeDef] = {}

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


def topological_sort(types: dict[str, TypeDef]) -> list[TypeDef]: 
	visited: set[str] = set()
	out: list[TypeDef] = []

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


def substitute(type_expr: TypeExpr, mapping: dict[str, TypeExpr]) -> TypeExpr:
	if isinstance(type_expr, TypeVarType):
		return mapping.get(type_expr.name, type_expr)

	if isinstance(type_expr, ListType):
		return ListType(substitute(type_expr.item, mapping))

	if isinstance(type_expr, DictType):
		return DictType(
			substitute(type_expr.key, mapping),
			substitute(type_expr.value, mapping)
		)

	if isinstance(type_expr, UnionTypeExpr):
		return UnionTypeExpr([
			substitute(x, mapping) for x in type_expr.options
		])

	if isinstance(type_expr, GenericRef):
		return GenericRef(
			fq_name=type_expr.fq_name,
			short_name=type_expr.short_name,
			args=[substitute(x, mapping) for x in type_expr.args]
		)

	return type_expr


def instantiate_generic(base: ClassDef | TypedDictDef, args: list[TypeExpr]) -> ClassDef | TypedDictDef:
	mapping = dict(zip(base.type_params, args))
	
	new_fields = [
		Field(
			name=f.name,
			type=substitute(f.type, mapping),
			nullable=f.nullable
		)
		for f in base.fields
	]

	if isinstance(base, ClassDef):
		return ClassDef(
			name=base.name,
			fq_name=base.fq_name,
			fields=new_fields,
			deps=base.deps,
			type_params=[],
			is_exported=base.is_exported
		)

	return TypedDictDef(
		name=base.name,
		fq_name=base.fq_name,
		fields=new_fields,
		deps=base.deps,
		type_params=[],
		is_exported=base.is_exported
	)


def collect_imports(type_defs: list[TypeDef], all_types: dict[str, TypeDef]):
	imports: dict[str, set[str]] = {} # module -> TypeDef names

	for t in type_defs:
		for dep in t.deps:
			if dep not in all_types:
				continue

			dep_type = all_types[dep]

			if dep_type.output_module == t.output_module:
				continue

			imports.setdefault(dep_type.output_module, set()).add(dep_type.name)
	
	return imports


def extract(config: MytsConfiguration):
	build = extract_mypy_graph(config.root)

	registry = extract_types(build)

	roots = [t for t in registry.values() if t.is_exported]

	shooken = resolve_dependencies(roots, registry)

	topologically_sorted = topological_sort(shooken)
	
	modules: dict[str, OutputModule] = {}
	for t in topologically_sorted:
		if t.output_module in modules:
			output_module = modules[t.output_module]
		else:
			output_module = OutputModule(
				name=t.output_module,
				type_defs=[],
				imports={}
			)
			modules[t.output_module] = output_module
		
		output_module.type_defs.append(t)
	
	for output_module in modules.values():
		output_module.imports = collect_imports(output_module.type_defs, shooken)

	convert_ir_to_ts_ir(
		modules,
		output_folder=config.output,
		group=config.group,
		output_file_name=config.output_file_name,
		trim_root=config.trim_root,
		preserve_structure=config.preserve_structure,
		dry_run=config.dry_run
	)