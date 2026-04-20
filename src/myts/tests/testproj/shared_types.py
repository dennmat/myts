import enum
from typing import TypedDict

class FakeStrEnum(enum.StrEnum):
	STRING_ONE = "string"
	STRING_TWO = "string2"
	STRING_THREE = "3"

class FakeIntEnum(enum.IntEnum):
	INT_ONE = 0
	INT_TWO = 1
	INT_THREE = 2

class AuthorTD(TypedDict):
	first_name: str
	last_name: str
	age: int
	city: FakeStrEnum

class BookTD(TypedDict):
	author: AuthorTD
	name: str
	isbn: str
	genre: FakeIntEnum
