from mypy.build import BuildResult
from mypy.nodes import TypeInfo


class BuildContext:
	result: BuildResult
	typeinfo_map: dict[str, TypeInfo] = {}

	def __init__(self, result: BuildResult):
		self.result = result
		self.typeinfo_map = {}
		self._index()

	def _index(self):
		for state in self.result.graph.values():
			if not state.tree:
				continue

			for sym in state.tree.names.values():
				node = sym.node

				if isinstance(node, TypeInfo):
					self.typeinfo_map[node.fullname] = node

	def get_typeinfo(self, fullname: str) -> TypeInfo | None:
		return self.typeinfo_map.get(fullname)
