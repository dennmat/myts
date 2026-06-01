from dataclasses import dataclass
import enum
from typing import Literal

from myts.core.types import MytsType


class SomeEnum(enum.IntEnum):
	ENUM1 = 1
	ENUM2 = 3
	ENUMB = enum.auto()
	ENUM3 = 5
	ENUMA = enum.auto()


type OtherUnion = Literal[4] | Literal[3]
type MyUnion = Literal["cat"] | Literal[5] | OtherUnion | None


@dataclass
class TestClassSimple(MytsType):
	wow: str
	woah: int
	cool: MyUnion


@dataclass
class WoahAnother(MytsType):
	neat: TestClassSimple
	neater_ino: SomeEnum


type MyGenericAlias[T] = list[T] | dict[str, T]


class UseMyGeneric[X](MytsType):
	still_generic: MyGenericAlias[X]
	less_generic: MyGenericAlias[int]
