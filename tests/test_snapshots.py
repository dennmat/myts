import difflib
import os
from pathlib import Path
import re
import subprocess
import sys


UPDATE_SNAPSHOTS = os.getenv("UPDATE_SNAPSHOTS") == "1"


def normalize(s: str) -> str:
	s = "\n".join(line.rstrip() for line in s.strip().splitlines())
	s = re.sub(r"// LAST GENERATED: .*", "// LAST GENERATED: <fixed>", s)
	return s


def run_myts(root: Path, output: Path) -> dict[str, str]:
	result = subprocess.run(
		[sys.executable, "-m", "myts", str(root), "-o", str(output)],
		capture_output=True,
		text=True,
	)

	print(result.stdout)

	assert result.returncode == 0


def read_dir(path: Path) -> dict[str, str]:
	return {
		str(p.relative_to(path)): p.read_text() for p in path.rglob("*") if p.is_file()
	}


def assert_with_diff(actual: str, expected: str):
	if actual != expected:
		diff = "\n".join(
			difflib.unified_diff(
				expected.splitlines(),
				actual.splitlines(),
				fromfile="expected",
				tofile="actual",
				lineterm="",
			)
		)
		assert False, f"\n{diff}"


def assert_dirs_equal(actual: dict[str, str], expected: dict[str, str]):
	actual_keys = set(actual)
	expected_keys = set(expected)

	if actual_keys != expected_keys:
		missing = expected_keys - actual_keys
		extra = actual_keys - expected_keys

		msg = [
			"If this is correct due to changes, run again with UPDATE_SNAPSHOTS=1 pytest"
		]
		if missing:
			msg.append(f"Missing files: {sorted(missing)}")
		if extra:
			msg.append(f"Unexpected files: {sorted(extra)}")

		assert False, "\n".join(msg)

	errors = []

	for key in sorted(expected_keys):
		actual_value = normalize(actual[key])
		expected_value = normalize(expected[key])

		if actual_value != expected_value:
			diff = "\n".join(
				difflib.unified_diff(
					expected_value.splitlines(),
					actual_value.splitlines(),
					fromfile=f"expected/{key}",
					tofile=f"actual/{key}",
					lineterm="",
				)
			)
			errors.append(f"\nDiff in {key}:\n{diff}")

	if errors:
		assert False, f"If this is correct due to changes, run again with UPDATE_SNAPSHOTS=1 pytest\n{chr(10).join(errors)}"  # chr(10) is \n


def assert_snapshot(project_name: str, tmp_path: Path):
	root = Path("./tests/projects") / project_name

	src = root / "src"
	expected_dir = root / "expected"

	project = src / project_name
	output = tmp_path / "output" / project_name

	run_myts(project, output)

	actual_dir = read_dir(output)

	if UPDATE_SNAPSHOTS:
		for key_path, value in actual_dir.items():
			output_path = expected_dir / key_path

			if not output_path.exists():
				output_path.parent.mkdir(parents=True, exist_ok=True)

			output_path.write_text(value)
		print("✅ Wrote to expected dir")
		return

	expected_dir = read_dir(expected_dir)
	assert_dirs_equal(actual_dir, expected_dir)


def test_basic(tmp_path: Path):
	assert_snapshot("basic", tmp_path)
