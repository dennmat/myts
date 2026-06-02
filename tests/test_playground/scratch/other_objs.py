from dataclasses import dataclass
import enum
from enum import Flag, auto
from typing import Generic, Literal, TypeVar

from myts.core.decorators import myts_export
from .shared_types import AuthorTD, BookTD, FakeIntEnum
from myts.core.types import MytsType as AliasedMyts


class NotADataclass[X, Y](AliasedMyts):
	x: X
	y: X | Y
	z: X | Y | None


T = TypeVar("T", str, int)


class EnumFlag(Flag):
	FLAG1 = auto()
	FLAG2 = auto()
	FLAG3 = auto()


@dataclass
class GenericData(Generic[T], AliasedMyts):
	content: NotADataclass[T, str]
	label: str
	test: int
	flag: EnumFlag


@dataclass
class MyOtherFakeClass(AliasedMyts):
	bleh: str
	this: list[int]
	that: list[dict[str, int]]
	gentest: GenericData[str]


@dataclass
class MyFakeBookShelf(AliasedMyts):
	books: list[BookTD]
	book: BookTD
	author: AuthorTD
	wow: Literal[FakeIntEnum.INT_TWO] | Literal["wow"]
	num_books: int | None
	cat: str | bool | int
	dog: int
	some_lits: Literal["Hi", "bye", 'no "not" no', None, True, 34, -32] | int


@myts_export()
class ForcedEnumExport(enum.IntEnum):
	do = 1
	it = 2
