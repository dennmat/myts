from dataclasses import dataclass
import enum

from myts.types import MytsType

class SomeEnum(enum.IntEnum):
	ENUM1 = 1
	ENUM2 = 3
	ENUM3 = 5

@dataclass
class TestClassSimple(MytsType):
	wow: str
	woah: int

@dataclass
class WoahAnother(MytsType):
	neat: TestClassSimple
	neater_ino: SomeEnum