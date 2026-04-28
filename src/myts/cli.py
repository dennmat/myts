import pathlib
import sys
import argparse
from pathlib import Path
import tomllib

from pydantic import ValidationError
from rich.pretty import pprint
from watchfiles import watch, Change

from myts.configs import default_and_merge_myts_configs
from myts.extractors.ts import extract_ts
from myts.types import MytsConfigurationInput

WATCH_IGNORE = {
	"__pycache__",
	".git",
	".venv",
	"venv",
	"dist",
	"build",
}


def watch_filter(_: Change, path: str) -> bool:
	if not any([path.endswith(ext) for ext in [".py", ".pyx", ".pyd"]]):
		return False

	return not any(part in WATCH_IGNORE for part in pathlib.Path(path).parts)


def main() -> None:
	parser = argparse.ArgumentParser(
		prog="Myts",
		description="MyPy to other type converter -- currently only supports Typescript",
		epilog="",
	)

	parser.add_argument(
		"root",
		type=Path,
		default=argparse.SUPPRESS,
		help="Path to py project root, defaults to current directory",
		nargs="?",
	)
	parser.add_argument(
		"-o",
		"--output",
		type=Path,
		default=argparse.SUPPRESS,
		help="Path to the output folder, defaults to ./myts-types/, if this is a relative path it is relative to root.",
	)
	parser.add_argument(
		"-w",
		"--watch",
		default=argparse.SUPPRESS,
		help="Actively watch for py changes and regenerate",
		action="store_true",
	)
	parser.add_argument(
		"-g",
		"--group",
		choices=["module", "single"],
		default=argparse.SUPPRESS,
		help="Module will use python module structure to determine output, single will simply output to a single file.",
	)
	parser.add_argument(
		"-tr",
		"--trim-root",
		default=argparse.SUPPRESS,
		help="Specify a pythonic path (i.e. my.project.path) that will be trimmed from paths in the output",
	)
	parser.add_argument(
		"-nf",
		"--no-folders",
		default=argparse.SUPPRESS,
		help="Will output flat into the output dir.",
		action="store_true",
	)
	parser.add_argument(
		"-ofn",
		"--output-file-name",
		default=argparse.SUPPRESS,
		help="Specifies the generated filename when group is set to 'single'",
	)
	parser.add_argument(
		"-dr",
		"--dry-run",
		default=argparse.SUPPRESS,
		action="store_true",
		help="Will print the output files to the console, but not actually write files. Ignored if --watch is on",
	)
	parser.add_argument("-c", "--config", default=argparse.SUPPRESS, type=Path)

	args = parser.parse_args()

	if "root" in args and not args.root.exists() or not args.root.is_dir():
		print(f"Provided root: {args.root} is not a valid directory.", file=sys.stderr)
		sys.exit(64)

	py_project_config = get_project_toml_config(args.root)

	config_at_root = get_config_at_root(
		args.root, config_path=args.config if "config" in args else None
	)

	args_config = MytsConfigurationInput(
		root=args.root if "root" in args else None,
		output=args.output if "output" in args else None,
		group=args.group if "group" in args else None,
		preserve_structure=not args.no_folders if "no_folders" in args else None,
		dry_run=args.dry_run if "dry_run" in args else None,
		output_file_name=args.output_file_name if "output_file_name" in args else None,
		trim_root=args.trim_root if "trim_root" in args else None,
	)

	config = default_and_merge_myts_configs(
		Path.cwd(),
		*[c for c in [py_project_config, config_at_root, args_config] if c is not None],
	)

	if not config.output.is_absolute():
		config.output = config.root / config.output

	if not config.output.exists():
		config.output.mkdir(parents=True)

	if not config.output.is_dir():
		print(f"Provided output: {config.output} is not a directory.", file=sys.stderr)
		sys.exit(64)

	print("Using configuration:")
	pprint(config.model_dump())

	extract_ts(config)

	if "watch" in args and args.watch:
		print("Watching")
		for _ in watch(config.root, watch_filter=watch_filter, debounce=300):
			extract_ts(config)


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


if __name__ == "__main__":
	main()
