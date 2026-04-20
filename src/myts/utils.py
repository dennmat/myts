from myts.types import EnumKind, EnumValue, PrimitiveType, TypeExpr, UnionTypeExpr


def is_subclass_of(info, fullname: str | tuple[str]) -> bool:
	"""
		Given an unknown obj and a fullname, this will determine if the py obj inherits from the fullname at any point.
	"""
	if not hasattr(info, 'mro'):
		return False
	
	check = (fullname,) if not isinstance(fullname, tuple) else fullname

	return any(base.fullname in check for base in info.mro)


def split_nullable(union: UnionTypeExpr) -> tuple[TypeExpr, bool]:
	non_null = [t for t in union.options if not isinstance(t, PrimitiveType) or t.name != 'None']
	is_optional = len(non_null) < len(union.options)

	if is_optional and len(non_null) == 1:
		return non_null[0], True
	
	return union, False


def detect_enum_kind(values: list[EnumValue]) -> EnumKind:
	types = {type(v.value) for v in values if v.value is not None}

	if types == {str}:
		return "str"
	
	if types <= {int}:
		return "int"
	
	return "mixed"
