from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias, Union

type GroupingMode = Literal['module', 'single']

@dataclass
class MytsConfiguration:
	root: Path
	output: Path
	group: GroupingMode
	preserve_structure: bool
	dry_run: bool
	output_file_name: str | None
	trim_root: str | None


JSON: TypeAlias = Union[
    dict[str, "JSON"],
    list["JSON"],
    str,
    int,
    float,
    bool,
    None
]

@dataclass
class PrimitiveType:
	name: Literal["str", "int", "bool", "float", "none", "any"]

@dataclass
class ListType:
	item: "TypeExpr"

@dataclass
class DictType:
	key: "TypeExpr"
	value: "TypeExpr"

@dataclass
class UnionTypeExpr:
	options: list["TypeExpr"]

@dataclass
class RefType:
	name: str
	fq_name: str

@dataclass
class TypeVarType:
	name: str

@dataclass
class LiteralValueType:
	value: str | int | bool | bytes | None

TypeExpr = PrimitiveType | ListType | DictType | UnionTypeExpr | RefType | TypeVarType

@dataclass
class Field:
	name: str
	type: TypeExpr
	nullable: bool = False

@dataclass
class GenericRef:
	fq_name: str
	short_name: str
	args: list[TypeExpr]


@dataclass
class ClassDef:
	name: str
	fq_name: str
	output_module: str
	fields: list[Field]
	deps: set[str]
	type_params: list[str]
	is_exported: bool

@dataclass
class TypedDictDef:
	name: str
	fq_name: str
	output_module: str
	fields: list[Field]
	deps: set[str]
	type_params: list[str]
	is_exported: bool

@dataclass
class EnumValue:
	name: str
	value: str | int

EnumKind = Literal["str", "int", "mixed"]

@dataclass
class EnumDef:
	kind: EnumKind
	name: str
	fq_name: str
	output_module: str
	values: list[EnumValue]
	deps: set[str]
	type_params: list[str]
	is_exported: bool

TypeDef = ClassDef | EnumDef | TypedDictDef

@dataclass
class OutputModule:
	name: str
	type_defs: list[TypeDef]
	imports: dict[str, set[str]]

class MytsType:
	"""
		Inherit from this type to include this class and any referenced enums or TypedDicts in the myts export
	"""
	pass
