from dataclasses import dataclass
import datetime
import os
from pathlib import Path
import json

import humps

from myts.config import MytsConfiguration
from myts.core.analyze import build_field_collector
from myts.core.ir import (
	AliasDef,
	AliasRef,
	ClassDef,
	DictType,
	EnumDef,
	ExportType,
	ListType,
	LiteralValue,
	PrimitiveType,
	RefType,
	TypeExpr,
	TypeParam,
	TypeVar,
	TypedDictDef,
	UnionTypeExpr,
	GenericRef,
)
from myts.core.types import AnalysisResult, GroupingMode
from myts.exporters.base import Exporter
from myts.exporters.ts.ir import (
	TSAliasDef,
	TSArray,
	TSEnumDef,
	TSEnumValue,
	TSField,
	TSGeneric,
	TSInterfaceDef,
	TSLiteralValue,
	TSModule,
	TSPrimitive,
	TSRef,
	TSType,
	TSTypeDef,
	TSTypeParam,
	TSTypeVar,
	TSUnion,
)


def to_ts_type(t: TypeExpr) -> TSType:
	if isinstance(t, PrimitiveType):
		return {
			"str": TSPrimitive("string"),
			"int": TSPrimitive("number"),
			"float": TSPrimitive("number"),
			"bool": TSPrimitive("boolean"),
			"None": TSPrimitive("null"),
			"Any": TSPrimitive("any"),
		}.get(t.name, TSPrimitive("any"))

	if isinstance(t, TypeVar):
		return TSTypeVar(name=t.name)

	if isinstance(t, LiteralValue):
		return TSLiteralValue(value=t.value)

	if isinstance(t, ListType):
		return TSArray(to_ts_type(t.item))

	if isinstance(t, DictType):
		return TSGeneric(name="Record", args=[to_ts_type(t.key), to_ts_type(t.value)])

	if isinstance(t, UnionTypeExpr):
		return TSUnion([to_ts_type(x) for x in t.options])

	if isinstance(t, RefType):
		return TSRef(humps.pascalize(t.name))

	if isinstance(t, GenericRef):
		return TSGeneric(
			name=humps.pascalize(t.short_name), args=[to_ts_type(x) for x in t.args]
		)

	if isinstance(t, AliasRef):
		return TSGeneric(
			name=humps.pascalize(t.short_name), args=[to_ts_type(x) for x in t.args]
		)

	return TSPrimitive("any")


def convert_myts_type_param_to_ts_type_param(myts_param: TypeParam) -> TSTypeParam:
	return TSTypeParam(
		name=myts_param.name,
		bound=to_ts_type(myts_param.bound) if myts_param.bound else None,
		constraints=[to_ts_type(constraint) for constraint in myts_param.constraints]
		if myts_param.constraints
		else None,
	)


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


def resolve_relative_import(from_module: str, to_module: str) -> str:
	from_path = module_to_file(from_module)
	to_path = module_to_file(to_module)

	rel = os.path.relpath(to_path, os.path.dirname(from_path))

	rel = rel.replace("\\", "/")
	rel = rel.removesuffix(".ts")

	if not rel.startswith("."):
		rel = "./" + rel

	return rel


@dataclass
class TSOutput:
	path: Path
	module: TSModule
	type_defs: TSTypeDef


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


class TSExporter(Exporter):
	def transform(
		self, analysis: AnalysisResult, config: MytsConfiguration
	) -> list[TSModule]:
		ts_modules: list[TSModule] = []

		collect_fields = build_field_collector(analysis.registry)

		for module in analysis.modules.values():
			converted_defs = []
			for type_def in module.registry.values():
				if isinstance(type_def, AliasDef):
					converted_defs.append(
						TSAliasDef(
							name=type_def.name,
							myts_key=type_def.fullname,
							target=to_ts_type(type_def.target),
							generic_args=[
								convert_myts_type_param_to_ts_type_param(v)
								for v in type_def.type_params
							],
						)
					)
				elif isinstance(type_def, EnumDef):
					converted_defs.append(
						TSEnumDef(
							name=type_def.name,
							myts_key=type_def.fullname,
							values=[
								TSEnumValue(name=v.name, value=v.value)
								for v in type_def.values
							],
						)
					)
				elif isinstance(type_def, ClassDef) or isinstance(
					type_def, TypedDictDef
				):
					fields = collect_fields(type_def.fullname)

					mapped_bases = [
						analysis.registry[base]
						for base in type_def.bases
						if base in analysis.registry
						and analysis.registry[base].export
						in (ExportType.FORCE_EXPORT, ExportType.AUTO)
					]

					converted_defs.append(
						TSInterfaceDef(
							name=humps.pascalize(type_def.name),
							myts_key=type_def.fullname,
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
				# elif UNION ALIAS?:
				# ...

			if len(converted_defs) > 0:
				ts_modules.append(
					TSModule(
						name=module.fullname,
						type_defs=converted_defs,
						imports=module.imports,
					)
				)

		return ts_modules

	def get_outputs(
		self, analysis: AnalysisResult, config: MytsConfiguration
	) -> list[
		TSOutput
	]:  # TODO name me better, add to base? figure out wwhat i do first might need a whole rename anyways
		outputs: list[TSOutput] = []
		for module in analysis.modules:
			output_file_path = get_output_file_path(
				module,
				output_folder=config.output,
				group=config.group,
				output_file_name=config.output_file_name,
				trim_root=config.trim_root,
				preserve_structure=config.preserve_structure,
			)

			outputs.append(
				TSOutput(
					path=output_file_path, module=module, type_defs=module.type_defs
				)
			)

		return outputs

	def emit_bases(self, bases: list[str]) -> str:
		if len(bases) == 0:
			return ""

		return f" extends {', '.join(bases) }"

	def emit_alias_def(self, type_def: TSAliasDef) -> list[str]:
		params = self.emit_type_params(type_def.generic_args)

		lines_out: list[str] = []
		lines_out.append(
			f"export declare type {type_def.name}{params} = {self.emit_type(type_def.target)};"
		)

		return lines_out

	def emit_interface_def(self, type_def: TSInterfaceDef) -> list[str]:
		lines_out: list[str] = []

		params = self.emit_type_params(type_def.generic_args)

		bases = self.emit_bases(type_def.bases)

		# TODO make interface vs type an option
		lines_out.append(f"export interface {type_def.name}{params}{bases} {{")

		for field in type_def.fields:
			whitespace = "\t"  # if tabs else use invalid stupid spaces
			lines_out.append(f"{whitespace}{field.name}: {self.emit_type(field.type)};")

		lines_out.append("}")

		return lines_out

	def emit_enum_def(self, tdef: TSEnumDef) -> list[str]:
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

	def emit_type_params(self, params: list[TSTypeParam]) -> str:
		if not params:
			return ""

		parts: list[str] = []

		for param in params:
			if param.constraints:
				union = " | ".join(
					self.emit_type(constraint_type)
					for constraint_type in param.constraints
				)
				parts.append(f"{param.name} extends {union}")

			elif param.bound:
				parts.append(f"{param.name} extends {self.emit_type(param.bound)}")

			else:
				parts.append(param.name)

		return f"<{ ', '.join(parts) }>"

	def emit_type(self, ts_type: TSType) -> str:
		if isinstance(ts_type, TSPrimitive):
			return ts_type.name

		if isinstance(ts_type, TSRef):
			return ts_type.name

		if isinstance(ts_type, TSTypeVar):
			return ts_type.name

		if isinstance(ts_type, TSArray):
			return f"Array<{ self.emit_type(ts_type.item) }>"

		if isinstance(ts_type, TSUnion):
			return f"{ ' | '.join(map(self.emit_type, ts_type.types)) }"

		if isinstance(ts_type, TSGeneric):
			if len(ts_type.args) > 0:
				return f"{ts_type.name}<{', '.join([self.emit_type(t) for t in ts_type.args])}>"
			else:
				return f"{ts_type.name}"

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

	def generate_outputs(
		self,
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
				TSOutput(
					path=output_file_path, module=module, type_defs=module.type_defs
				)
			)

		return outputs

	def emit_imports(
		self, imports: dict[str, set[str]], current_module: str
	) -> list[str]:
		lines = []

		for module, names in sorted(imports.items()):
			path = resolve_relative_import(current_module, module)
			joined = ", ".join(sorted(names))

			lines.append(f'import type {{ {joined} }} from "{path}";')

		return lines

	def emit_output(self, output: TSOutput, include_imports: bool = True):
		lines_out: list[str] = []

		if include_imports:
			import_lines = self.emit_imports(output.module.imports, output.module.name)

			if len(import_lines):
				import_lines.append("")

			lines_out += import_lines

		for t in output.type_defs:
			if isinstance(t, TSInterfaceDef):
				lines_out += self.emit_interface_def(t)
				lines_out.append("")
			elif isinstance(t, TSEnumDef):
				lines_out += self.emit_enum_def(t)
				lines_out.append("")
			elif isinstance(t, TSAliasDef):
				lines_out += self.emit_alias_def(t)
				lines_out.append("")

		return "\n".join(lines_out) + "\n"

	def output_single(self, outputs: list[TSOutput], dry_run: bool = False):
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
				output_content = self.emit_output(output, include_imports=False)
				fhndl.write(output_content)

	def output_module(self, outputs: list[TSOutput], dry_run: bool = False):
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

				output_content = self.emit_output(output, include_imports=True)
				fhndl.write(output_content)

	def output_writer(
		self, outputs: list[TSOutput], group: GroupingMode, dry_run: bool = False
	):
		if len(outputs) == 0:
			print("No output to write.")
			return

		if group == "module":
			self.output_module(outputs, dry_run)
		elif group == "single":
			self.output_single(outputs, dry_run)

	def emit(self, modules: list[TSModule], config: MytsConfiguration):
		outputs = self.generate_outputs(
			modules,
			output_folder=config.output,
			group=config.group,
			output_file_name=config.output_file_name,
			trim_root=config.trim_root,
			preserve_structure=config.preserve_structure,
		)

		self.output_writer(outputs, config.group, config.dry_run)
