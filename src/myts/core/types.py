from dataclasses import dataclass
from typing import Literal

from myts.core.ir import Module, TypeDef

type GroupingMode = Literal["module", "single"]


@dataclass
class AnalysisResult:
	modules: dict[str, Module]
	registry: dict[str, TypeDef]


class MytsType:
	"""
	Inherit from this type to include this class and any referenced enums or TypedDicts in the myts export
	"""

	pass
