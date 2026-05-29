from mypy.build import BuildResult


class BuildContext:
	result: BuildResult

	def __init__(self, result: BuildResult):
		self.result = result
