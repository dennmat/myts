from dataclasses import asdict, dataclass
import json
import datetime
import os
from pathlib import Path

import humps

from myts.types import ClassDef, DictType, EnumDef, EnumKind, GenericRef, GroupingMode, ListType, LiteralValueType, MytsConfiguration, OutputModule, PrimitiveType, RefType, TypeDef, TypeExpr, TypeVarType, TypedDictDef, UnionTypeExpr

@dataclass
class TSUnion:
	types: list["TSType"]

@dataclass
class TSPrimitive:
	name: str

@dataclass
class TSArray:
	item: "TSType"

@dataclass
class TSRef:
	name: str

@dataclass
class TSGeneric:
	name: str
	args: list["TSType"]

@dataclass
class TSLiteralValue:
	value: str | int | bool | bytes | None

@dataclass
class TSTypeVar:
	name: str

TSType = TSUnion | TSPrimitive | TSArray | TSRef | TSGeneric | TSTypeVar

@dataclass
class TSField:
	name: str
	type: TSType
	optional: bool = False

@dataclass
class TSClassDef:
	name: str
	py_fq_name: str
	py_name: str
	output_module: str
	fields: list[TSField]
	generic_args: list[TSTypeVar]
	as_interface: bool = False

@dataclass
class TSEnumValue:
	name: str
	value: str | int

@dataclass
class TSEnumDef:
	py_enum_ir: EnumDef
	name: str
	values: list[TSEnumValue]

TSTypeDef = TSClassDef

def to_ts_type(t: TypeExpr) -> TSType:
	if isinstance(t, PrimitiveType):
		return {
			"str": TSPrimitive("string"),
			"int": TSPrimitive("number"),
			"float": TSPrimitive("number"),
			"bool": TSPrimitive("boolean"),
			"None": TSPrimitive("null"),
			"Any": TSPrimitive("any"),
		}.get(t.name, TSPrimitive('any'))
	
	if isinstance(t, TypeVarType):
		return TSTypeVar(name=t.name)

	if isinstance(t, LiteralValueType):
		return TSLiteralValue(value=t.value)
	
	if isinstance(t, ListType):
		return TSArray(to_ts_type(t.item))

	if isinstance(t, DictType):
		return TSGeneric(
			name="Record",
			args=[to_ts_type(t.key), to_ts_type(t.value)]
		)
	
	if isinstance(t, UnionTypeExpr):
		return TSUnion([to_ts_type(x) for x in t.options])
	
	if isinstance(t, RefType):
		return TSRef(humps.pascalize(t.name))
	
	if isinstance(t, GenericRef):
		return TSGeneric(
			name=humps.pascalize(t.short_name),
			args=[to_ts_type(x) for x in t.args]
		)
	
	return TSPrimitive("any")

@dataclass
class TSOutput:
	path: Path
	module: OutputModule
	type_defs: TSTypeDef

def relative_import(from_module: str, to_module: str) -> str:
	from_path = module_to_file(from_module)
	to_path = module_to_file(to_module)

	rel = os.path.relpath(to_path, os.path.dirname(from_path))

	rel = rel.replace("\\", "/")
	rel = rel.removesuffix(".ts")

	if not rel.startswith("."):
		rel = "./" + rel
	
	return rel

def emit_imports(imports, current_module) -> list[str]:
	lines = []

	for module, names in sorted(imports.items()):
		path = relative_import(current_module, module)
		joined = ", ".join(sorted(names))

		lines.append(f'import type {{ {joined} }} from "{path}"')

	return lines

def ts_type_to_str(ts_type: TSType) -> str:
	if isinstance(ts_type, TSPrimitive):
		return ts_type.name
	
	if isinstance(ts_type, TSRef):
		return ts_type.name
	
	if isinstance(ts_type, TSTypeVar):
		return ts_type.name

	if isinstance(ts_type, TSArray):
		return f"Array<{ ts_type_to_str(ts_type.item) }>"
	
	if isinstance(ts_type, TSUnion):
		return f"{ ' | '.join(map(ts_type_to_str, ts_type.types)) }"
	
	if isinstance(ts_type, TSGeneric):
		return f"{ts_type.name}<{", ".join([ts_type_to_str(t) for t in ts_type.args])}>"
	
	if isinstance(ts_type, TSLiteralValue):
		val = ts_type.value
		
		if val is None:
			return 'null'
		if isinstance(val, int) or isinstance(val, bool):
			return str(val).lower()
		if isinstance(val, bytes):
			return bytes.decode() # TODO maybe make this an option or something? TS doesnt have byte literals
		if isinstance(val, str):
			return json.dumps(val)

	return "any"

def emit_ts_class_def(tdef: TSClassDef) -> list[str]:
	lines_out: list[str] = []

	# TODO make interface vs type an option
	if len(tdef.generic_args) == 0:
		lines_out.append(f"export type {tdef.name} = {{")
	else:
		lines_out.append(f"export type {tdef.name}<{', '.join([v.name for v in tdef.generic_args])}> = {{")

	for field in tdef.fields:
		whitespace = "\t" # if tabs else use invalid stupid spaces
		lines_out.append(f"{whitespace}{field.name}: {ts_type_to_str(field.type)};")

	lines_out.append("};")
	
	return lines_out

def emit_ts_enum_def(tdef: TSEnumDef) -> list[str]:
	lines_out: list[str] = []

	# TODO make interface vs type an option
	lines_out.append(f"export const {tdef.name} = {{")
	
	for enum_value in tdef.values:
		whitespace = "\t" # if tabs else use invalid stupid spaces
		val = enum_value.value

		if val is None:
			val = f'"{enum_value.name}"'
		elif isinstance(val, bool):
			val = "true" if val else "false"
		elif isinstance(val, str):
			val = f'"{enum_value.value}"'
		
		lines_out.append(f"{whitespace}{enum_value.name}: {val},")

	lines_out.append("} as const;")
	lines_out.append(f"export type {tdef.name} = typeof {tdef.name}[keyof typeof {tdef.name}];")
	
	return lines_out

def ts_output_to_ts(output: TSOutput, include_imports: bool = True) -> str:
	#relative_imports
	lines_out: list[str] = []

	import_lines = emit_imports(output.module.imports, output.module.name)

	if len(import_lines):
		import_lines.append("")

	lines_out += import_lines

	for t in output.type_defs:
		if isinstance(t, TSClassDef):
			lines_out += emit_ts_class_def(t)
			lines_out.append("")
		elif isinstance(t, TSEnumDef):
			lines_out += emit_ts_enum_def(t)
			lines_out.append("")

	return "\n".join(lines_out) + "\n"

def module_to_file(
	module: str,
	preserve_structure: bool = True,
	trim_root: str | None = None
) -> Path:
	if trim_root is not None and preserve_structure:
		module = module.removeprefix(trim_root)
		if module.startswith('.'):
			module = module.lstrip('.')
	elif not preserve_structure:
		return module.split(".")[-1] + ".ts"

	return module.replace(".", "/") + ".ts"

def get_output_file(
	module: OutputModule,
	output_folder: Path,
	group: GroupingMode,
	output_file_name: str | None = None,
	trim_root: str | None = None,
	preserve_structure: bool = True
) -> Path:
	if group == 'single':
		out_name = output_file_name if output_file_name else 'types.ts'
		return output_folder / out_name
	
	return output_folder / module_to_file(
		module.name,
		preserve_structure=preserve_structure,
		trim_root=trim_root
	)

def convert_ir_to_ts_ir(
	modules: dict[str, OutputModule],
	output_folder: Path,
	group: GroupingMode,
	output_file_name: str | None = None,
	trim_root: str | None = None,
	preserve_structure: bool = True,
	dry_run: bool = False
):
	ts_outputs: list[TSOutput] = []

	for module in modules.values():
		converted_type_defs = []
		for tdef in module.type_defs:
			if isinstance(tdef, ClassDef):
				converted_type_defs.append(
					TSClassDef(
						name=humps.pascalize(tdef.name),
						py_fq_name=tdef.fq_name,
						py_name=tdef.name,
						output_module=tdef.output_module,
						generic_args=[TSTypeVar(v.name) for v in tdef.type_params],
						fields=[TSField(humps.camelize(f.name), to_ts_type(f.type), optional=f.nullable) for f in tdef.fields]
					)
				)
			elif isinstance(tdef, TypedDictDef):
				converted_type_defs.append(
					TSClassDef(
						name=humps.pascalize(tdef.name),
						py_fq_name=tdef.fq_name,
						py_name=tdef.name,
						output_module=tdef.output_module,
						generic_args=[TSTypeVar(v.name) for v in tdef.type_params],
						fields=[TSField(humps.camelize(f.name), to_ts_type(f.type), optional=f.nullable) for f in tdef.fields]
					)
				)
			elif isinstance(tdef, EnumDef):
				converted_type_defs.append(
					TSEnumDef(
						name=humps.pascalize(tdef.name),
						py_enum_ir=tdef,
						values=[TSEnumValue(name=v.name, value=v.value) for v in tdef.values]
					)
				)

		output_file = get_output_file(
			module,
			output_folder=output_folder,
			group=group,
			output_file_name=output_file_name,
			trim_root=trim_root,
			preserve_structure=preserve_structure
		)
		
		ts_outputs.append(
			TSOutput(
				path=output_file,
				module=module,
				type_defs=converted_type_defs
			)
		)
	
	output_writer(ts_outputs, group, dry_run)

def output_single(
	outputs: list[TSOutput],
	dry_run: bool = False
):
	output_path = outputs[0].path
	if dry_run:
		print(output_path)
		return
	
	with open(output_path, 'w') as fhndl:
		fhndl.write("\n".join(
			[
				"// AUTO-GENERATED FILE - DO NOT EDIT",
				f"// LAST-GENERATED: {datetime.datetime.now().isoformat()}",
				""
			]
		))

		for output in outputs:
			output_content = ts_output_to_ts(output, include_imports=False)
			fhndl.write(output_content)

def output_module(
	outputs: list[TSOutput],
	dry_run: bool = False
):
	if dry_run:
		for out in outputs:
			print(out.path)
		return

	for output in outputs:
		with open(output.path, 'w') as fhndl:
			fhndl.write("\n".join(
				[
					"// AUTO-GENERATED FILE - DO NOT EDIT",
					f"// LAST-GENERATED: {datetime.datetime.now().isoformat()}",
					""
				]
			))
			
			output_content = ts_output_to_ts(output, include_imports=True)
			fhndl.write(output_content)

def output_writer(
	outputs: list[TSOutput],
	group: GroupingMode,
	dry_run: bool = False
):
	if len(outputs) == 0:
		print("No output to write.")
		return

	if group == 'module':
		output_module(outputs, dry_run)
	elif group == 'single':
		output_single(outputs, dry_run)
