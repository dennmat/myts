import pathlib
import sys
import argparse
from pathlib import Path

from watchfiles import watch, Change

from myts.extractors.ts import extract_ts
from myts.types import MytsConfiguration

WATCH_IGNORE = {
	"__pycache__",
	".git",
	".venv",
	"venv",
	"dist",
	"build",
}


def watch_filter(change: Change, path: str) -> bool:
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
		"-r",
		"--root",
		type=Path,
		default=Path.cwd(),
		help="Path to py project root, defaults to current directory",
		required=False,
	)
	parser.add_argument(
		"-o",
		"--output",
		type=Path,
		default=Path.cwd() / "myts-types",
		help="Path to the output folder, defaults to ./myts-types/",
		required=True,
	)
	parser.add_argument(
		"-w",
		"--watch",
		help="Actively watch for py changes and regenerate",
		action="store_true",
	)
	parser.add_argument(
		"-g",
		"--group",
		choices=["module", "single"],
		default="module",
		help="Module will use python module structure to determine output, single will simply output to a single file.",
	)
	parser.add_argument(
		"-tr",
		"--trim-root",
		default=None,
		help="Specify a pythonic path (i.e. my.project.path) that will be trimmed from paths in the output",
	)
	parser.add_argument(
		"-nf",
		"--no-folders",
		help="Will output flat into the output dir.",
		action="store_true",
	)
	parser.add_argument(
		"-ofn",
		"--output-file-name",
		default=None,
		help="Specifies the generated filename when group is set to 'single'",
	)
	parser.add_argument(
		"-dr",
		"--dry-run",
		action="store_true",
		help="Will print the output files to the console, but not actually write files. Ignored if --watch is on",
	)

	args = parser.parse_args()

	if not args.output.exists():
		args.output.mkdir(parents=True)

	if not args.output.is_dir():
		print(f"Provided output: {args.output} is not a directory.", file=sys.stderr)
		sys.exit(2)

	if not args.root.exists() or not args.root.is_dir():
		print(f"Provided root: {args.root} is not a valid directory.", file=sys.stderr)
		sys.exit(2)

	config = MytsConfiguration(
		root=args.root,
		output=args.output,
		group=args.group,
		preserve_structure=not args.no_folders,
		dry_run=args.dry_run,
		output_file_name=args.output_file_name,
		trim_root=args.trim_root,
	)

	config.root = Path(__file__).resolve().parent / "tests" / "testproj"

	extract_ts(config)

	if args.watch:
		print("Watching")
		for _ in watch(config.root, watch_filter=watch_filter, debounce=300):
			extract_ts(config)


if __name__ == "__main__":
	main()
