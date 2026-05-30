import itertools

from myts.core.ir import ExportType, Module, TypeDef


def topological_sort(types: dict[str, TypeDef]) -> list[TypeDef]:
	"""
	Sorts the type tree by first found dependencies.

	This becomes important for module resolution order.
	"""
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
	"""
	Travels `roots` to build a map of all TypeDefs all roots are relient on.

	Accumulates all required TypeDefs to satisfy all roots.
	"""
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
	"""
	Resolves what imports a `myts.core.ir.Module` will require given it's "local" TypeDef's.

	Will skip dependencies marked as `ExportType.EXCLUDE`.

	Argument `type_defs` should only be scoped down to just the ones in the Module.
	Argument `registry` should be the full map of all known TypeDefs.
	"""
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


def distill_modules(
	roots: list[str], registry: dict[str, TypeDef]
) -> dict[str, Module]:
	"""
	Assembles `myts.core.ir.Module` objects grouped with their TypeDefs and required imports.
	"""
	resolved = resolve_dependencies(roots, registry)

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

	return modules
