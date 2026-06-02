from abc import ABC
from dataclasses import dataclass

from myts.core.types import AnalysisResult


@dataclass
class BaseTypeDef:
	name: str


class Exporter(ABC):
	def transform(self, analysis: AnalysisResult) -> list[BaseTypeDef]:
		raise NotImplementedError

	def emit(self, ir: list[BaseTypeDef]):
		raise NotImplementedError
