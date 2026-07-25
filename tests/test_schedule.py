from __future__ import annotations

import subprocess
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


def test_build_plist_contains_expected_fields():
    xml = schedule.build_plist(23, 50, ["tokentracer", "collect", "--lookback", "1"])
    assert "<string>com.ai-token-tracer</string>" in xml
    assert "<integer>23</integer>" in xml
    assert "<integer>50</integer>" in xml
    assert "<string>tokentracer</string>" in xml
    assert "<string>collect</string>" in xml


def test_schedule_macos_writes_plist_and_loads(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(schedule.subprocess, "run",
                         lambda args, **kw: calls.append(args) or subprocess.CompletedProcess(args, 0))
    monkeypatch.setattr(schedule, "_PLIST_PATH", tmp_path / "LaunchAgents" / f"{schedule.LABEL}.plist")
    monkeypatch.setattr(schedule.shutil, "which", lambda name: "/usr/local/bin/tokentracer")

    schedule.schedule_macos(23, 50)

    assert schedule._PLIST_PATH.exists()
    assert "<integer>23</integer>" in schedule._PLIST_PATH.read_text()
    assert calls[0][:2] == ["launchctl", "unload"]
    assert calls[-1][:2] == ["launchctl", "load"]


def test_unschedule_macos_removes_existing_job(monkeypatch, tmp_path):
    plist = tmp_path / f"{schedule.LABEL}.plist"
    plist.write_text("<plist></plist>")
    monkeypatch.setattr(schedule, "_PLIST_PATH", plist)
    calls = []
    monkeypatch.setattr(schedule.subprocess, "run",
                         lambda args, **kw: calls.append(args) or subprocess.CompletedProcess(args, 0))

    result = schedule.unschedule_macos()

    assert result is True
    assert not plist.exists()
    assert calls[0][:2] == ["launchctl", "unload"]


def test_unschedule_macos_noop_when_nothing_registered(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule, "_PLIST_PATH", tmp_path / "missing.plist")
    result = schedule.unschedule_macos()
    assert result is False


def test_schedule_windows_calls_schtasks_create(monkeypatch):
    calls = []
    monkeypatch.setattr(schedule.subprocess, "run",
                         lambda args, **kw: calls.append(args) or subprocess.CompletedProcess(args, 0))
    monkeypatch.setattr(schedule.shutil, "which", lambda name: "C:\\tools\\tokentracer.exe")

    schedule.schedule_windows(23, 50)

    assert calls[0][:3] == ["schtasks", "/Create", "/F"]
    assert "ai-token-tracer" in calls[0]
    assert "23:50" in calls[0]


def test_unschedule_windows_deletes_existing_task(monkeypatch):
    calls = []

    def fake_run(args, **kw):
        calls.append(args)
        if args[:2] == ["schtasks", "/Query"]:
            return subprocess.CompletedProcess(args, 0)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(schedule.subprocess, "run", fake_run)

    result = schedule.unschedule_windows()

    assert result is True
    assert calls[0][:2] == ["schtasks", "/Query"]
    assert calls[1][:3] == ["schtasks", "/Delete", "/F"]


def test_unschedule_windows_noop_when_nothing_registered(monkeypatch):
    monkeypatch.setattr(schedule.subprocess, "run",
                         lambda args, **kw: subprocess.CompletedProcess(args, 1))
    result = schedule.unschedule_windows()
    assert result is False
