from pathlib import Path

from myts.core import extract_modules, extract_mypy_graph
from myts.types import MytsConfiguration


def test_extract_mypy_graph():
	root = Path("tests/projects/basic")
	build = extract_mypy_graph(root)

	assert len(build.errors) == 0


def test_extract_modules_module(tmp_path):
	config = MytsConfiguration(
		root=Path("tests/projects/basic"),
		output=tmp_path / "temm",
		group="module",
		preserve_structure=True,
		dry_run=False,
		output_file_name=None,
		trim_root=None,
	)

	registry, modules = extract_modules(config)

	assert "basic.accounts.models" in modules
