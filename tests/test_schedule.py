from __future__ import annotations

import sys
from pathlib import Path

import pytest

from src import schedule


def test_parse_time_valid():
    assert schedule.parse_time("23:50") == (23, 50)
    assert schedule.parse_time("00:00") == (0, 0)
    assert schedule.parse_time("9:05") == (9, 5)


def test_parse_time_rejects_bad_format():
    with pytest.raises(ValueError):
        schedule.parse_time("2350")
    with pytest.raises(ValueError):
        schedule.parse_time("not-a-time")


def test_parse_time_rejects_out_of_range():
    with pytest.raises(ValueError):
        schedule.parse_time("24:00")
    with pytest.raises(ValueError):
        schedule.parse_time("10:60")


def test_resolve_executable_prefers_path(monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: "/usr/local/bin/tokentracer")
    assert schedule.resolve_executable() == ["/usr/local/bin/tokentracer"]


def test_resolve_executable_falls_back_to_tracker_py(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: None)
    fake_tracker = tmp_path / "tracker.py"
    fake_tracker.write_text("# tracker")
    monkeypatch.setattr(schedule, "_TRACKER_PY_PATH", fake_tracker)
    assert schedule.resolve_executable() == [sys.executable, str(fake_tracker)]


def test_resolve_executable_raises_when_neither_found(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: None)
    monkeypatch.setattr(schedule, "_TRACKER_PY_PATH", tmp_path / "missing_tracker.py")
    with pytest.raises(FileNotFoundError):
        schedule.resolve_executable()
