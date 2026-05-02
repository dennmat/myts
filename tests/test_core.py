import itertools
from pathlib import Path

from myts.core import (
	extract_modules,
	extract_mypy_graph,
	extract_roots,
	extract_types,
	resolve_dependencies,
)
from myts.types import MytsConfiguration, MytsExportType, MytsTypeDef


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
	assert "basic.streamables.models" in modules

	assert "basic.common.types.TSExport" in registry
	assert "basic.accounts.models.User" in registry

	user_model = registry["basic.accounts.models.User"]

	assert isinstance(user_model, MytsTypeDef)
	assert user_model.export == MytsExportType.ROOT
	assert len(user_model.fields) > 0, "User model failed to have it's fields extracted"

	ts_export = registry["basic.common.types.TSExport"]

	assert isinstance(ts_export, MytsTypeDef)
	assert (
		ts_export.export == MytsExportType.INTERNAL
	), "Decorator is mis-configured for TSExport in sample project, or core is not extracting decorator args correctly"
	assert (
		len(ts_export.fields) == 0
	), "TSExport has fields extracted when it should not"


def test_extract_types():
	build = extract_mypy_graph(Path("tests/projects/basic"))
	registry = extract_types(build)

	assert len(registry.keys()) > 0, "Received an empty registry"


def test_extract_roots():
	build = extract_mypy_graph(Path("tests/projects/basic"))
	registry = extract_types(build)

	roots = extract_roots(registry)

	ensure_matches = (
		("User", "basic.accounts.models.User"),
		("Account", "basic.accounts.models.Account"),
		("MovieBase", "basic.streamables.models.MovieBase"),
		("ComedyMovie", "basic.streamables.models.ComedyMovie"),
	)

	for name, fq_name in ensure_matches:
		assert any(
			r.name == name and r.fq_name == fq_name for r in roots
		), f"No match for {name} ({fq_name})"

	for root in roots:
		assert root.export in (
			MytsExportType.ROOT,
			MytsExportType.EXPORT,
		), "Invalid export type included in roots"


def test_resolve_dependencies():
	build = extract_mypy_graph(Path("tests/projects/basic"))
	registry = extract_types(build)
	roots = extract_roots(registry)

	min_root_deps = itertools.chain(*[r.deps for r in roots])

	resolved = resolve_dependencies(roots, registry)

	assert (
		"basic.common.types.NotIncluded" not in resolved
	), "Extraneous dependencies were added"

	assert all(
		r in resolved for r in min_root_deps
	), "Not all root dependencies were resolved"
