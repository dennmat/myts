from pathlib import Path

import pytest
from myts.cli import main


def test_success(tmp_path: Path, capsys):
	root = Path.cwd() / "./tests/projects/basic"
	main([str(root.resolve()), "--output", str(tmp_path.resolve())])
	captured = capsys.readouterr()
	assert "Myts all done." in captured.out


def test_help(capsys):
	with pytest.raises(SystemExit):
		main(["-h"])

	captured = capsys.readouterr()
	assert "MyPy to other type converter" in captured.out
