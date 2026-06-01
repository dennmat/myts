from mypy.build import BuildResult, State
from mypy.nodes import (
	AssignmentStmt,
	CallExpr,
	Expression,
	IntExpr,
	MemberExpr,
	NameExpr,
	OpExpr,
	StrExpr,
	TypeAlias,
	TypeInfo,
	Var,
)
from mypy.types import (
	AnyType,
	Instance,
	LiteralType,
	NoneType,
	Type,
	TypeAliasType,
	TypeVarType,
	TypedDictType,
	UnionType,
	get_proper_type,
)

from myts.core.ast import ASTContext
from myts.core.ir import (
	AliasDef,
	AliasRef,
	DictType,
	EnumDef,
	EnumSpecialValue,
	EnumValue,
	ExportType,
	Field,
	GenericRef,
	ListType,
	LiteralValue,
	PrimitiveType,
	RefType,
	TypeDef,
	TypeExpr,
	TypeParam,
	TypeVar,
	TypedDictDef,
	UnionTypeExpr,
	ClassDef as MytsClassDef,
)
from myts.utils.mypy import is_enum, is_subclass_of, is_typeddict, split_nullable


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


def extract_type_params(
	root_module: str, info: TypeInfo, aliasdef_registry: dict[str, AliasDef]
) -> list[TypeParam]:
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
				bound = map_type(root_module, type_var.upper_bound, aliasdef_registry)

		if hasattr(type_var, "values") and type_var.values:
			constraints = [
				map_type(root_module, value, aliasdef_registry)
				for value in type_var.values
			]

		params.append(TypeParam(name=name, bound=bound, constraints=constraints))

	return params


def extract_alias_type_params(
	root_module: str, info: TypeAlias, aliasdef_registry: dict[str, AliasDef]
) -> list[TypeParam]:
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
				bound = map_type(root_module, type_var.upper_bound, aliasdef_registry)

		if hasattr(type_var, "values") and type_var.values:
			constraints = [
				map_type(root_module, value, aliasdef_registry)
				for value in type_var.values
			]

		params.append(TypeParam(name=name, bound=bound, constraints=constraints))

	return params


def parse_export_args(call: CallExpr) -> ExportType:
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


def parse_myts_export(info: TypeInfo) -> ExportType | None:
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
				return parse_export_args(decorator)

			if isinstance(callee, MemberExpr) and callee.name == "myts_export":
				return parse_export_args(decorator)


def extract_types_from_state(
	root_module: str,
	state: State,
	aliasdef_registry: dict[str, AliasDef],
	ast: ASTContext,
) -> tuple[list[TypeDef], list[TypeDef]]:
	"""
	`root_module` is required to exclude modules that don't come from the targeted module

	Crawls the tree from a `State` object and extracts relevant Myts `TypeDef`s

	Returns a list of all extracted relevant TypeDefs, a list of all identified `roots`.

	Roots being TypeDefs that define the base of the Myts export. Other types are conditionally included based on their export field or if they're referenced from a root type.
	"""
	tree = state.tree
	results: list[TypeDef] = []
	roots: list[TypeDef] = []

	def is_root_export(type_def: TypeDef) -> bool:
		return type_def.is_entrypoint or type_def.export == ExportType.FORCE_EXPORT

	for sym in tree.names.values():
		node = sym.node

		if not node.fullname.startswith(root_module + "."):
			continue

		if isinstance(node, TypeInfo):
			type_def = extract(root_module, node.fullname, node, aliasdef_registry, ast)
			if type_def:
				if is_root_export(type_def):
					roots.append(type_def)
				results.append(type_def)
		elif isinstance(node, TypeAlias):
			mapped_t = map_type(root_module, node.target, aliasdef_registry)
			deps = collect_refs(mapped_t)

			alias_def = AliasDef(
				fullname=node.fullname,
				name=node.name,
				deps=deps,
				export=ExportType.AUTO,
				target=mapped_t,
				is_entrypoint=False,
				type_params=extract_alias_type_params(
					root_module, node, aliasdef_registry
				),
			)

			aliasdef_registry[node.fullname] = alias_def
			results.append(alias_def)

	return results, roots


def extract_enum_value(
	sym: Var, stmt: AssignmentStmt
) -> int | str | None | EnumSpecialValue:
	# 1. Preferred: mypy resolved value
	final_value = getattr(sym, "final_value", None)
	if isinstance(final_value, (int, str)):
		return final_value

	if sym.type and isinstance(sym.type, LiteralType):
		return sym.type.value

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
		elif rvalue.name == "None":
			return None

	# 4. Member access (rare but possible)
	if isinstance(rvalue, MemberExpr):
		node = rvalue.node
		if isinstance(node, Var):
			ref_val = getattr(node, "final_value", None)
			if isinstance(ref_val, (int, str)):
				return ref_val

	# 5. OpExpr (Arithmetic) A = 1 + 5
	if isinstance(rvalue, OpExpr):
		...  # TODO recurse and resolve OpExpr(left=IntExpr|FloatExpr|Member, right=SameAsLeft, op="+")

	# 6. auto() or function calls → unresolved
	# - may remove this, might be cleaner to just not support
	if isinstance(rvalue, CallExpr):
		if sym.type.type.fullname == "enum.auto":
			return EnumSpecialValue.AUTO

		return None

	return None


def extract_enum(
	fullname: str,
	info: TypeInfo,
	ast: ASTContext,
) -> EnumDef:
	export = parse_myts_export(info)

	if export is None:
		export = ExportType.AUTO

	values: list[EnumValue] = []

	collected_values: list[tuple[str, str | int | None | EnumSpecialValue]] = []
	for name in info.names.keys():
		stmt = ast.cache.get((fullname, name))

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

		collected_values.append((name, extract_enum_value(sym.node, stmt)))

	# Resolve AUTO's matching Python's defaults as closely as possible
	next_value = 1
	for name, value in collected_values:
		if value == EnumSpecialValue.AUTO:
			value = next_value

		values.append(EnumValue(name, value))

		if isinstance(value, int):
			next_value = value + 1

	return EnumDef(
		name=info.name,
		fullname=fullname,
		deps=set(),
		export=export,
		is_entrypoint=False,
		values=values,
	)


def extract_class(
	root_module: str,
	fullname: str,
	info: TypeInfo,
	aliasdef_registry: dict[str, AliasDef],
) -> MytsClassDef:
	export = parse_myts_export(info)
	is_myts_subclass = is_subclass_of(info, "myts.core.types.MytsType")

	if export is None:
		export = ExportType.AUTO

	bases = []

	for base in info.bases:
		base_type = get_proper_type(base)

		if isinstance(base_type, Instance):
			if base.type.fullname.startswith(root_module + "."):
				bases.append(base.type.fullname)

	fields = []
	deps: set[str] = set()

	for name, sym in info.names.items():
		if not isinstance(sym.node, Var):
			continue

		node = sym.node

		if name.startswith("_"):  # Make as option
			continue

		if node.type is None:
			continue

		mapped_t = map_type(root_module, node.type, aliasdef_registry)

		nullable = False
		if isinstance(mapped_t, UnionTypeExpr):
			mapped_t, nullable = split_nullable(mapped_t)

		fields.append(Field(node.name, mapped_t, nullable))
		deps |= collect_refs(mapped_t)

	return MytsClassDef(
		export=export,
		name=info.name,
		fullname=fullname,
		bases=bases,
		fields=fields,
		deps=deps,
		type_params=extract_type_params(root_module, info, aliasdef_registry),
		is_entrypoint=is_myts_subclass,
		from_typeddict=False,
	)


def extract_typeddict(
	root_module: str,
	fullname: str,
	info: TypeInfo,
	aliasdef_registry: dict[str, AliasDef],
) -> TypedDictDef:
	export = parse_myts_export(info)
	is_myts_subclass = is_subclass_of(info, "myts.core.types.MytsType")

	if export is None:
		export = ExportType.AUTO

	bases = []

	for base in info.bases:
		base_type = get_proper_type(base)

		if isinstance(base_type, Instance):
			if base.type.fullname.startswith(root_module + "."):
				bases.append(base.type.fullname)

	fields = []
	deps: set[str] = set()

	typeddict = info.typeddict_type

	for name, sym in typeddict.items.items():
		if name.startswith("_"):
			continue

		mapped_t = map_type(root_module, sym, aliasdef_registry)

		nullable = False
		if isinstance(mapped_t, UnionTypeExpr):
			mapped_t, nullable = split_nullable(mapped_t)

		fields.append(Field(name, mapped_t, nullable))
		deps |= collect_refs(mapped_t)

	return MytsClassDef(
		export=export,
		name=info.name,
		fullname=fullname,
		bases=bases,
		fields=fields,
		deps=deps,
		is_entrypoint=is_myts_subclass,
		type_params=extract_type_params(root_module, info, aliasdef_registry),
		from_typeddict=True,
	)


def extract(
	root_module: str,
	fullname: str,
	info: TypeInfo,
	aliasdef_registry: dict[str, AliasDef],
	ast: ASTContext,
) -> TypeDef:
	if is_enum(info):
		return extract_enum(fullname, info, ast)

	if is_typeddict(info):
		return extract_typeddict(root_module, fullname, info, aliasdef_registry)

	return extract_class(root_module, fullname, info, aliasdef_registry)


def map_semantic_type(
	root_module: str, semantic_type: Type, aliasdef_registry: dict[str, AliasDef]
) -> TypeExpr:
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
			return ListType(
				map_type(root_module, semantic_type.args[0], aliasdef_registry)
			)

		if fullname == "builtins.dict":
			return DictType(
				map_type(root_module, semantic_type.args[0], aliasdef_registry),
				map_type(root_module, semantic_type.args[1], aliasdef_registry),
			)

		if not fullname.startswith(root_module):
			return PrimitiveType("any")

		if semantic_type.args:
			return GenericRef(
				fullname,
				semantic_type.type.name,
				args=[
					map_type(root_module, i, aliasdef_registry)
					for i in semantic_type.args
				],
			)

		return RefType(name=semantic_type.type.name, fullname=fullname)

	if isinstance(semantic_type, TypeVarType):
		return TypeVar(semantic_type.name)

	if isinstance(semantic_type, UnionType):
		return UnionTypeExpr(
			[map_type(root_module, i, aliasdef_registry) for i in semantic_type.items]
		)

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


def map_type(
	root_module: str, info: Type, aliasdef_registry: dict[str, AliasDef]
) -> TypeExpr:
	if isinstance(info, TypeAliasType):
		fullname = info.alias.fullname
		if fullname in aliasdef_registry and isinstance(
			aliasdef_registry[fullname], AliasDef
		):
			if len(info.args) > 0:
				args = [map_type(root_module, i, aliasdef_registry) for i in info.args]
			else:
				args = []

			return AliasRef(short_name=info.alias.name, fullname=fullname, args=args)

	return map_semantic_type(root_module, info, aliasdef_registry)


def extract_ir(
	root_module: str, build: BuildResult, ast: ASTContext
) -> tuple[list[str], dict[str, TypeDef]]:
	roots: list[str] = []
	registry: dict[str, TypeDef] = {}
	aliasdef_registry: dict[str, AliasDef] = {}

	for state in build.graph.values():
		tree = getattr(state, "tree", None)
		if tree is None:
			continue

		types, source_roots = extract_types_from_state(
			root_module, state, aliasdef_registry, ast
		)

		roots += source_roots

		for typ in types:
			registry[typ.fullname] = typ

	return roots, registry
