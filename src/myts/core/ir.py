from dataclasses import dataclass
from enum import Enum, auto
from typing import Literal


class ExportType(Enum):
	AUTO = "auto"
	FORCE_EXPORT = "force_export"
	EXCLUDE = "exclude"


@dataclass(slots=True)
class PrimitiveType:
	name: Literal["str", "int", "bool", "float", "none", "any"]


@dataclass(slots=True)
class ListType:
	item: "TypeExpr"


@dataclass(slots=True)
class DictType:
	key: "TypeExpr"
	value: "TypeExpr"


@dataclass(slots=True)
class TupleType:
	items: list["TypeExpr"]
	unbounded: bool


@dataclass(slots=True)
class UnionTypeExpr:
	options: list["TypeExpr"]


@dataclass(slots=True)
class RefType:
	name: str
	fullname: str


@dataclass(slots=True)
class TypeVar:
	name: str


@dataclass(slots=True)
class LiteralValue:
	value: str | int | bool | bytes | None


TypeExpr = PrimitiveType | ListType | DictType | UnionTypeExpr | RefType | TypeVar


@dataclass(slots=True)
class GenericRef:
	fullname: str
	short_name: str
	args: list[TypeExpr]


@dataclass(slots=True)
class AliasRef:
	fullname: str
	short_name: str
	args: list[TypeExpr]


@dataclass(slots=True)
class Field:
	name: str
	type: TypeExpr
	nullable: bool = False

	def __repr__(self) -> str:
		return f"{self.name} -> {self.type}"


@dataclass(slots=True)
class TypeParam:
	name: str
	bound: TypeExpr | None
	constraints: list[TypeExpr] | None


@dataclass(slots=True)
class TypeDef:
	fullname: str
	name: str
	deps: set[str]
	export: ExportType
	is_entrypoint: bool

	@property
	def output_module(self) -> str:
		# A bit naive but will work for now
		return ".".join(self.fullname.split(".")[:-1])

	def __repr__(self) -> str:
		return f"{self.fullname} ({self.__class__.__name__})"


@dataclass(slots=True)
class AliasDef(TypeDef):
	target: "TypeExpr"
	type_params: list[TypeParam]


@dataclass(slots=True)
class ClassDef(TypeDef):
	fields: list[Field]
	bases: list[str]
	type_params: list[TypeParam]
	from_typeddict: bool

	def __repr__(self) -> str:
		base = super().__repr__()

		fields = "\n".join([f"\t{f.__repr__()}" for f in self.fields])

		return f"{base}\n{fields}"


class EnumSpecialValue(Enum):
	AUTO = auto()


@dataclass(slots=True)
class EnumValue:
	name: str
	value: str | int | None


@dataclass(slots=True)
class EnumDef(TypeDef):
	values: list[EnumValue]


@dataclass(slots=True)
class TypedDictDef(TypeDef):
	fields: list[Field]
	bases: list[str]
	type_params: list[TypeParam]


@dataclass(slots=True)
class Module:
	fullname: str
	registry: dict[str, TypeDef]
	imports: dict[str, set[str]]
