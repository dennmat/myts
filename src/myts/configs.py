from pathlib import Path

from myts.types import MytsConfiguration, MytsConfigurationInput


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
