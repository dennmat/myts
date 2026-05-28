from typing import Literal, overload


@overload
def myts_export(): ...


@overload
def myts_export(export: bool): ...


@overload
def myts_export(mode: Literal["internal", "exclude"]): ...


def myts_export(*args, **kwargs):
	def simple(cls):
		return cls

	return simple
