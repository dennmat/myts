from dataclasses import dataclass
import enum
from typing import Generic, Literal, TypeVar

from myts.decorators import myts_export
from myts.tests.testproj.shared_types import AuthorTD, BookTD, FakeIntEnum
from myts.types import MytsType


class NotADataclass[X, Y](MytsType):
	x: X
	y: X | Y
	z: X | Y | None


T = TypeVar("T", str, int)


@dataclass
class GenericData(Generic[T], MytsType):
	content: NotADataclass[T, str]
	label: str
	test: int


@dataclass
class MyOtherFakeClass(MytsType):
	this: list[int]
	that: list[dict[str, int]]
	gentest: GenericData[str]


@dataclass
class MyFakeBookShelf(MytsType):
	books: list[BookTD]
	book: BookTD
	author: AuthorTD
	wow: Literal[FakeIntEnum.INT_TWO] | Literal["wow"]
	num_books: int | None
	cat: str | bool | int
	dog: int
	some_lits: Literal["Hi", "bye", 'no "not" no', None, True, 34, -32] | int


@myts_export
class ForcedEnumExport(enum.IntEnum):
	do = 1
	it = 2
