from dataclasses import dataclass


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
	myts_key: str
	bases: list[str]
	output_module: str
	fields: list[TSField]
	generic_args: list[TSTypeParam]


@dataclass
class TSEnumValue:
	name: str
	value: str | int


@dataclass
class TSAliasDef:
	name: str
	myts_key: str
	target: TSType
	generic_args: list[TSTypeParam]


@dataclass
class TSTypeTypeDef:  # Sometimes names are bad; this is `type MyTSType = {...};`
	name: str
	myts_key: str
	bases: list[str]
	output_module: str
	fields: list[TSField]
	generic_args: list[TSTypeParam]


@dataclass
class TSEnumDef:
	name: str
	myts_key: str
	name: str
	values: list[TSEnumValue]


TSTypeDef = TSInterfaceDef | TSEnumDef | TSTypeTypeDef


@dataclass
class TSModule:  # This is more of a mirror of myts' Module, not a literal TS module
	name: str
	type_defs: list[TSTypeDef]
	imports: dict[str, set[str]]
