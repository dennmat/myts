from abc import ABC
from dataclasses import dataclass

from myts.config import MytsConfiguration
from myts.core.types import AnalysisResult


@dataclass
class BaseTypeDef:
	name: str


class Exporter(ABC):
	def transform(
		self, analysis: AnalysisResult, config: MytsConfiguration
	) -> list[BaseTypeDef]:
		raise NotImplementedError

	def emit(self, ir: list[BaseTypeDef], config: MytsConfiguration):
		raise NotImplementedError
