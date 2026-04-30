from dataclasses import dataclass
import json
import datetime
import os
from pathlib import Path

import humps

from myts.core import build_field_collector, extract_modules
from myts.types import (
	MytsConfiguration,
	MytsDefType,
	MytsDictType,
	MytsExportType,
	MytsGenericRef,
	GroupingMode,
	MytsListType,
	MytsLiteralValue,
	MytsModule,
	MytsPrimitiveType,
	MytsRefType,
	MytsTypeDef,
	MytsTypeExpr,
	MytsTypeParam,
	MytsTypeVar,
	MytsUnionTypeExpr,
)


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
class TSTypeParam:
	name: str
	bound: TSType | None
	constraints: list[TSType] | None


@dataclass
class TSField:
	name: str
	type: TSType
	optional: bool = False


@dataclass
class TSInterfaceDef:
	name: str
	py_fq_name: str
	py_name: str
	bases: list[str]
	output_module: str
	fields: list[TSField]
	generic_args: list[TSTypeParam]


@dataclass
class TSTypeDef:
	name: str
	py_fq_name: str
	py_name: str
	bases: list[str]
	output_module: str
	fields: list[TSField]
	generic_args: list[TSTypeParam]


@dataclass
class TSEnumValue:
	name: str
	value: str | int


@dataclass
class TSEnumDef:
	py_enum_ir: MytsTypeDef
	name: str
	values: list[TSEnumValue]


@dataclass
class TSModule:
	name: str
	type_defs: list[TSTypeDef]
	imports: dict[str, set[str]]


def to_ts_type(t: MytsTypeExpr) -> TSType:
	if isinstance(t, MytsPrimitiveType):
		return {
			"str": TSPrimitive("string"),
			"int": TSPrimitive("number"),
			"float": TSPrimitive("number"),
			"bool": TSPrimitive("boolean"),
			"None": TSPrimitive("null"),
			"Any": TSPrimitive("any"),
		}.get(t.name, TSPrimitive("any"))

	if isinstance(t, MytsTypeVar):
		return TSTypeVar(name=t.name)

	if isinstance(t, MytsLiteralValue):
		return TSLiteralValue(value=t.value)

	if isinstance(t, MytsListType):
		return TSArray(to_ts_type(t.item))

	if isinstance(t, MytsDictType):
		return TSGeneric(name="Record", args=[to_ts_type(t.key), to_ts_type(t.value)])

	if isinstance(t, MytsUnionTypeExpr):
		return TSUnion([to_ts_type(x) for x in t.options])

	if isinstance(t, MytsRefType):
		return TSRef(humps.pascalize(t.name))

	if isinstance(t, MytsGenericRef):
		return TSGeneric(
			name=humps.pascalize(t.short_name), args=[to_ts_type(x) for x in t.args]
		)

	return TSPrimitive("any")


@dataclass
class TSOutput:
	path: Path
	module: MytsModule
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

		lines.append(f'import type {{ {joined} }} from "{path}";')

	return lines


def emit_ts_type(ts_type: TSType) -> str:
	if isinstance(ts_type, TSPrimitive):
		return ts_type.name

	if isinstance(ts_type, TSRef):
		return ts_type.name

	if isinstance(ts_type, TSTypeVar):
		return ts_type.name

	if isinstance(ts_type, TSArray):
		return f"Array<{ emit_ts_type(ts_type.item) }>"

	if isinstance(ts_type, TSUnion):
		return f"{ ' | '.join(map(emit_ts_type, ts_type.types)) }"

	if isinstance(ts_type, TSGeneric):
		return f"{ts_type.name}<{", ".join([emit_ts_type(t) for t in ts_type.args])}>"

	if isinstance(ts_type, TSLiteralValue):
		val = ts_type.value

		if val is None:
			return "null"
		if isinstance(val, int) or isinstance(val, bool):
			return str(val).lower()
		if isinstance(val, bytes):
			return bytes.decode()  # TODO maybe make this an option or something? TS doesnt have byte literals
		if isinstance(val, str):
			return json.dumps(val)

	return "any"


def emit_ts_type_params(params: list[TSTypeParam]) -> str:
	if not params:
		return ""

	parts: list[str] = []

	for param in params:
		if param.constraints:
			union = " | ".join(
				emit_ts_type(constraint_type) for constraint_type in param.constraints
			)
			parts.append(f"{param.name} extends {union}")

		elif param.bound:
			parts.append(f"{param.name} extends {emit_ts_type(param.bound)}")

		else:
			parts.append(param.name)

	return f"<{ ', '.join(parts) }>"


def emit_ts_bases(bases: list[str]) -> str:
	if len(bases) == 0:
		return ""

	return f" extends {', '.join(bases) }"


def emit_ts_interface_def(type_def: TSInterfaceDef) -> list[str]:
	lines_out: list[str] = []

	params = emit_ts_type_params(type_def.generic_args)

	bases = emit_ts_bases(type_def.bases)

	# TODO make interface vs type an option
	lines_out.append(f"export interface {type_def.name}{params}{bases} {{")

	for field in type_def.fields:
		whitespace = "\t"  # if tabs else use invalid stupid spaces
		lines_out.append(f"{whitespace}{field.name}: {emit_ts_type(field.type)};")

	lines_out.append("}")

	return lines_out


def emit_ts_enum_def(tdef: TSEnumDef) -> list[str]:
	lines_out: list[str] = []

	# TODO make interface vs type an option
	lines_out.append(f"export const {tdef.name} = {{")

	for enum_value in tdef.values:
		whitespace = "\t"  # if tabs else use invalid stupid spaces
		val = enum_value.value

		if val is None:
			val = f'"{enum_value.name}"'
		elif isinstance(val, bool):
			val = "true" if val else "false"
		elif isinstance(val, str):
			val = f'"{enum_value.value}"'

		lines_out.append(f"{whitespace}{enum_value.name}: {val},")

	lines_out.append("} as const;")
	lines_out.append(
		f"export type {tdef.name} = typeof {tdef.name}[keyof typeof {tdef.name}];"
	)

	return lines_out


def ts_output_to_ts(output: TSOutput, include_imports: bool = True) -> str:
	lines_out: list[str] = []

	if include_imports:
		import_lines = emit_imports(output.module.imports, output.module.name)

		if len(import_lines):
			import_lines.append("")

		lines_out += import_lines

	for t in output.type_defs:
		if isinstance(t, TSInterfaceDef):
			lines_out += emit_ts_interface_def(t)
			lines_out.append("")
		elif isinstance(t, TSEnumDef):
			lines_out += emit_ts_enum_def(t)
			lines_out.append("")

	return "\n".join(lines_out) + "\n"


def module_to_file(
	module: str, preserve_structure: bool = True, trim_root: str | None = None
) -> Path:
	if trim_root is not None and preserve_structure:
		module = module.removeprefix(trim_root)
		if module.startswith("."):
			module = module.lstrip(".")
	elif not preserve_structure:
		return module.split(".")[-1] + ".ts"

	return module.replace(".", "/") + ".ts"


def get_output_file_path(
	module: TSModule,
	output_folder: Path,
	group: GroupingMode,
	output_file_name: str | None = None,
	trim_root: str | None = None,
	preserve_structure: bool = True,
) -> Path:
	if group == "single":
		out_name = output_file_name if output_file_name else "types.ts"
		return output_folder / out_name

	return output_folder / module_to_file(
		module.name, preserve_structure=preserve_structure, trim_root=trim_root
	)


def convert_myts_type_param_to_ts_type_param(myts_param: MytsTypeParam) -> TSTypeParam:
	return TSTypeParam(
		name=myts_param.name,
		bound=to_ts_type(myts_param.bound) if myts_param.bound else None,
		constraints=[to_ts_type(constraint) for constraint in myts_param.constraints]
		if myts_param.constraints
		else None,
	)


def convert_myts_ir_to_ts_ir(
	modules: dict[str, MytsModule], myts_registry: dict[str, MytsTypeDef]
) -> list[TSModule]:
	ts_modules: list[TSModule] = []

	collect_fields = build_field_collector(myts_registry)

	for module in modules.values():
		converted_type_defs = []
		for type_def in module.type_defs:
			if type_def.type == MytsDefType.ENUM:
				converted_type_defs.append(
					TSEnumDef(
						name=type_def.name,
						py_enum_ir=type_def,
						values=[
							TSEnumValue(name=v.name, value=v.value)
							for v in type_def.enum_values
						],
					)
				)
			elif type_def.type == MytsDefType.OBJECT:
				fields = collect_fields(type_def.fq_name)

				mapped_bases = [
					myts_registry[base]
					for base in type_def.bases
					if base in myts_registry
					and myts_registry[base].export
					in (MytsExportType.EXPORT, MytsExportType.ROOT)
				]

				converted_type_defs.append(
					TSInterfaceDef(
						name=humps.pascalize(type_def.name),
						py_fq_name=type_def.fq_name,
						py_name=type_def.name,
						output_module=type_def.output_module,
						bases=[humps.pascalize(base.name) for base in mapped_bases],
						generic_args=[
							convert_myts_type_param_to_ts_type_param(v)
							for v in type_def.type_params
						],
						fields=[
							TSField(
								humps.camelize(f.name),
								to_ts_type(f.type),
								optional=f.nullable,
							)
							for f in fields
						],
					)
				)
			elif type_def.type in (MytsDefType.UNION, MytsDefType.ALIAS):
				...

		if len(converted_type_defs) > 0:
			ts_modules.append(
				TSModule(
					name=module.name,
					type_defs=converted_type_defs,
					imports=module.imports,
				)
			)

	return ts_modules


def generate_ts_outputs(
	modules: list[TSModule],
	output_folder: Path,
	group: GroupingMode,
	output_file_name: str | None = None,
	trim_root: str | None = None,
	preserve_structure: bool = True,
) -> list[TSOutput]:
	outputs: list[TSOutput] = []
	for module in modules:
		output_file_path = get_output_file_path(
			module,
			output_folder=output_folder,
			group=group,
			output_file_name=output_file_name,
			trim_root=trim_root,
			preserve_structure=preserve_structure,
		)

		outputs.append(
			TSOutput(path=output_file_path, module=module, type_defs=module.type_defs)
		)

	return outputs


def output_single(outputs: list[TSOutput], dry_run: bool = False):
	output_path = outputs[0].path
	if dry_run:
		print(output_path)
		return

	with open(output_path, "w") as fhndl:
		fhndl.write(
			"\n".join(
				[
					"// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT",
					f"// LAST GENERATED: {datetime.datetime.now().isoformat()}",
					"",
				]
			)
		)

		for output in outputs:
			output_content = ts_output_to_ts(output, include_imports=False)
			fhndl.write(output_content)


def output_module(outputs: list[TSOutput], dry_run: bool = False):
	if dry_run:
		for out in outputs:
			print(out.path)
		return

	generated_date = datetime.datetime.now().isoformat()
	for output in outputs:
		if not output.path.parent.exists():
			output.path.parent.mkdir(parents=True)

		with open(output.path, "w") as fhndl:
			fhndl.write(
				"\n".join(
					[
						"// AUTO-GENERATED FILE BY MYTS - DO NOT EDIT",
						f"// LAST GENERATED: {generated_date}",
						"",
					]
				)
			)

			output_content = ts_output_to_ts(output, include_imports=True)
			fhndl.write(output_content)


def output_writer(outputs: list[TSOutput], group: GroupingMode, dry_run: bool = False):
	if len(outputs) == 0:
		print("No output to write.")
		return

	if group == "module":
		output_module(outputs, dry_run)
	elif group == "single":
		output_single(outputs, dry_run)


def extract_ts(config: MytsConfiguration):
	myts_registry, myts_modules = extract_modules(config)

	ts_modules = convert_myts_ir_to_ts_ir(myts_modules, myts_registry)

	ts_outputs = generate_ts_outputs(
		ts_modules,
		output_folder=config.output,
		group=config.group,
		output_file_name=config.output_file_name,
		trim_root=config.trim_root,
		preserve_structure=config.preserve_structure,
	)

	output_writer(ts_outputs, config.group, config.dry_run)
