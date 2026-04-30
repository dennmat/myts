from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, TypeAlias, Union

from pydantic import BaseModel

type GroupingMode = Literal["module", "single"]


class MytsUnsetType:
	__slots__ = ()

	def __repr__(self) -> str:
		return "Unset"


MytsUnset = MytsUnsetType()


class MytsConfiguration(BaseModel):
	root: Path
	output: Path
	group: GroupingMode
	preserve_structure: bool
	dry_run: bool
	output_file_name: str | None = None
	trim_root: str | None = None


class MytsConfigurationInput(BaseModel):
	root: Path | None = None
	output: Path | None = None
	group: GroupingMode | None = None
	preserve_structure: bool | None = None
	dry_run: bool | None = None
	output_file_name: str | None = None
	trim_root: str | None = None


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
class MytsTypeParam:
	name: str
	bound: MytsTypeExpr | None
	constraints: list[MytsTypeExpr] | None


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


class MytsDefType(Enum):
	OBJECT = "object"
	UNION = "union"
	ALIAS = "alias"
	ENUM = "enum"


class MytsExportType(Enum):
	ROOT = "root"
	EXPORT = "export"
	INTERNAL = "internal"
	EXCLUDE = "exclude"


@dataclass
class MytsEnumValue:
	name: str
	value: str | int


# WIP this will replace ClassDef/TypedDictDef and EnumDef
@dataclass
class MytsTypeDef:
	export: MytsExportType
	type: MytsDefType
	name: str
	fq_name: str
	output_module: str
	bases: list[str]
	fields: list[MytsField]
	deps: set[str]
	type_params: list[MytsTypeParam]
	enum_values: list[MytsEnumValue]


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
