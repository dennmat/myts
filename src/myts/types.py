from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias, Union

type GroupingMode = Literal["module", "single"]


@dataclass
class MytsConfiguration:
	root: Path
	output: Path
	group: GroupingMode
	preserve_structure: bool
	dry_run: bool
	output_file_name: str | None
	trim_root: str | None


JSON: TypeAlias = Union[dict[str, "JSON"], list["JSON"], str, int, float, bool, None]


@dataclass
class MytsPrimitiveType:
	name: Literal["str", "int", "bool", "float", "none", "any"]


@dataclass
class MytsListType:
	item: "MytsTypeExpr"


@dataclass
class MytsDictType:
	key: "MytsTypeExpr"
	value: "MytsTypeExpr"


@dataclass
class MytsUnionTypeExpr:
	options: list["MytsTypeExpr"]


@dataclass
class MytsRefType:
	name: str
	fq_name: str


@dataclass
class MytsTypeVar:
	name: str


@dataclass
class MytsLiteralValue:
	value: str | int | bool | bytes | None


MytsTypeExpr = (
	MytsPrimitiveType
	| MytsListType
	| MytsDictType
	| MytsUnionTypeExpr
	| MytsRefType
	| MytsTypeVar
)


@dataclass
class MytsField:
	name: str
	type: MytsTypeExpr
	nullable: bool = False


@dataclass
class MytsGenericRef:
	fq_name: str
	short_name: str
	args: list[MytsTypeExpr]


@dataclass
class MytsClassDef:
	name: str
	fq_name: str
	output_module: str
	fields: list[MytsField]
	deps: set[str]
	type_params: list[str]
	is_exported: bool


@dataclass
class MytsTypedDictDef:
	name: str
	fq_name: str
	output_module: str
	fields: list[MytsField]
	deps: set[str]
	type_params: list[str]
	is_exported: bool


@dataclass
class MytsEnumValue:
	name: str
	value: str | int


EnumKind = Literal["str", "int", "mixed"]


@dataclass
class MytsEnumDef:
	kind: EnumKind
	name: str
	fq_name: str
	output_module: str
	values: list[MytsEnumValue]
	deps: set[str]
	type_params: list[str]
	is_exported: bool


MytsTypeDef = MytsClassDef | MytsEnumDef | MytsTypedDictDef


@dataclass
class MytsModule:
	name: str
	type_defs: list[MytsTypeDef]
	imports: dict[str, set[str]]


class MytsType:
	"""
	Inherit from this type to include this class and any referenced enums or TypedDicts in the myts export
	"""

	pass
