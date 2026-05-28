from mypy.nodes import TypeInfo

from myts.core.ir import PrimitiveType, TypeExpr, UnionTypeExpr


def is_subclass_of(info: TypeInfo, fullname: str | tuple[str]) -> bool:
	"""
	Given an unknown obj and a fullname, this will determine if the py obj inherits from the fullname at any point.
	"""
	if not hasattr(info, "mro"):
		return False

	check = (fullname,) if not isinstance(fullname, tuple) else fullname

	return any(base.fullname in check for base in info.mro)


def is_enum(info: TypeInfo) -> bool:
	return is_subclass_of(info, ("enum.Enum", "enum.IntEnum", "enum.StrEnum"))


def is_typeddict(info: TypeInfo) -> bool:
	return info.typeddict_type is not None


def split_nullable(union: UnionTypeExpr) -> tuple[TypeExpr, bool]:
	non_null = [
		t for t in union.options if not isinstance(t, PrimitiveType) or t.name != "None"
	]
	is_optional = len(non_null) < len(union.options)

	if is_optional and len(non_null) == 1:
		return non_null[0], True

	return union, False
