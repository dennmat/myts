from pathlib import Path
import sys
import tomllib

from pydantic import BaseModel, ValidationError

from myts.core.types import GroupingMode


class MytsUnsetType:
	__slots__ = ()

	def __repr__(self) -> str:
		return "Unset"


MytsUnset = MytsUnsetType()


class MytsConfiguration(BaseModel):
	root: Path
	output: Path
	group: GroupingMode
	preserve_structure: bool
	dry_run: bool
	output_file_name: str | None = None
	trim_root: str | None = None


class MytsConfigurationInput(BaseModel):
	root: Path | None = None
	output: Path | None = None
	group: GroupingMode | None = None
	preserve_structure: bool | None = None
	dry_run: bool | None = None
	output_file_name: str | None = None
	trim_root: str | None = None


def default_and_merge_myts_configs(
	default_root: Path, *configs: MytsConfigurationInput | MytsConfiguration
) -> MytsConfiguration:
	"""
	Pass configs in order of least precendence to most.
	The last config will overwrite
	"""
	defaults = dict(
		root=default_root,
		output=default_root / "myts-types",
		group="module",
		preserve_structure=True,
		dry_run=False,
	)

	merged = {}
	for config in configs:
		merged.update(config.model_dump(exclude_none=True))

	for key, value in defaults.items():
		if key not in merged:
			merged[key] = value

	return MytsConfiguration(**merged)


def get_project_toml_config(root: Path) -> MytsConfigurationInput | None:
	proj_toml_path = root / "pyproject.toml"

	if not proj_toml_path.exists():
		return None

	with proj_toml_path.open("rb") as fhndl:
		try:
			config_data = tomllib.load(fhndl)
		except tomllib.TOMLDecodeError:
			print(
				"Invalid TOML in pyproject.toml",
				file=sys.stderr,
			)
			sys.exit(65)

	try:
		myts_config_data = config_data["tool"]["myts"]
	except KeyError:
		return None

	try:
		config = MytsConfigurationInput.model_validate(myts_config_data)
	except ValidationError:
		print(
			f"Invalid configuration provided in [tool.myts] in {proj_toml_path.resolve()}"
		)
		sys.exit(65)

	return config


def get_config_at_root(
	root: Path, config_path: Path | None = None
) -> MytsConfigurationInput | None:
	if config_path is None:
		config_path = root / "myts.toml"

	if not config_path.exists() or not config_path.is_file():
		return None

	with config_path.open("rb") as fhndl:
		try:
			config_data = tomllib.load(fhndl)
		except tomllib.TOMLDecodeError:
			print(
				f"Invalid TOML in found myts config @ {config_path.resolve()}",
				file=sys.stderr,
			)
			return None

	try:
		config = MytsConfigurationInput.model_validate(config_data)
	except ValidationError:
		print(f"Invalid configuration provided in {config_path.resolve()}")
		sys.exit(65)

	return config
