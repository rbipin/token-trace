"""Tests for .github/scripts/set_whimsy_version.py (run in a temp copy of the layout)."""
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "set_whimsy_version.py"
PYPROJECT = 'name = "whimsy"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'


def _run(tmp_path: Path, tag: str) -> subprocess.CompletedProcess:
    target = tmp_path / "packages" / "whimsy" / "pyproject.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(PYPROJECT)
    return subprocess.run(
        [sys.executable, str(SCRIPT), tag], cwd=tmp_path, capture_output=True, text=True
    )


def test_sets_version_from_tag(tmp_path):
    result = _run(tmp_path, "whimsy-v1.2.3")
    assert result.returncode == 0, result.stderr
    text = (tmp_path / "packages" / "whimsy" / "pyproject.toml").read_text()
    assert 'version = "1.2.3"' in text
    assert 'requires-python = ">=3.11"' in text


@pytest.mark.parametrize("tag", ["v1.2.3", "whimsy-v1.2", "whimsy-1.2.3", "whimsy-v1.2.3-rc1", ""])
def test_bad_tag_exits_nonzero_and_leaves_file_unchanged(tmp_path, tag):
    result = _run(tmp_path, tag)
    assert result.returncode != 0
    assert (tmp_path / "packages" / "whimsy" / "pyproject.toml").read_text() == PYPROJECT


def test_missing_version_line_exits_nonzero(tmp_path):
    target = tmp_path / "packages" / "whimsy"
    target.mkdir(parents=True)
    (target / "pyproject.toml").write_text('name = "whimsy"\n')
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "whimsy-v1.0.0"], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode != 0
