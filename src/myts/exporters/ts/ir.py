from dataclasses import dataclass


@dataclass(slots=True)
class TSUnion:
	types: list["TSType"]


@dataclass(slots=True)
class TSPrimitive:
	name: str


@dataclass(slots=True)
class TSArray:
	item: "TSType"


@dataclass(slots=True)
class TSRef:
	name: str


@dataclass(slots=True)
class TSGeneric:
	name: str
	args: list["TSType"]


@dataclass(slots=True)
class TSLiteralValue:
	value: str | int | bool | bytes | None


@dataclass(slots=True)
class TSTypeVar:
	name: str


TSType = TSUnion | TSPrimitive | TSArray | TSRef | TSGeneric | TSTypeVar


@dataclass(slots=True)
class TSTypeParam:
	name: str
	bound: TSType | None
	constraints: list[TSType] | None


@dataclass(slots=True)
class TSField:
	name: str
	type: TSType
	optional: bool = False


@dataclass(slots=True)
class TSInterfaceDef:
	name: str
	myts_key: str
	bases: list[str]
	output_module: str
	fields: list[TSField]
	generic_args: list[TSTypeParam]


@dataclass(slots=True)
class TSEnumValue:
	name: str
	value: str | int


@dataclass(slots=True)
class TSAliasDef:
	name: str
	myts_key: str
	target: TSType
	generic_args: list[TSTypeParam]


@dataclass(slots=True)
class TSTypeTypeDef:  # Sometimes names are bad; this is `type MyTSType = {...};`
	name: str
	myts_key: str
	bases: list[str]
	output_module: str
	fields: list[TSField]
	generic_args: list[TSTypeParam]


@dataclass(slots=True)
class TSEnumDef:
	name: str
	myts_key: str
	name: str
	values: list[TSEnumValue]


TSTypeDef = TSInterfaceDef | TSEnumDef | TSTypeTypeDef


@dataclass(slots=True)
class TSModule:  # This is more of a mirror of myts' Module, not a literal TS module
	name: str
	type_defs: list[TSTypeDef]
	imports: dict[str, set[str]]
