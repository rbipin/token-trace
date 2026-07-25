from __future__ import annotations

import argparse

import pytest

from src.commands.schedule import ScheduleCommand, UnscheduleCommand


def _args(**kw):
    ns = argparse.Namespace()
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def test_schedule_invalid_time_returns_error(monkeypatch, capsys):
    monkeypatch.setattr("src.commands.schedule.platform.system", lambda: "Darwin")
    cmd = ScheduleCommand()
    code = cmd.run(_args(time="25:99"))
    assert code == 1
    assert "invalid time" in capsys.readouterr().err


def test_schedule_dispatches_to_macos(monkeypatch):
    calls = []
    monkeypatch.setattr("src.commands.schedule.platform.system", lambda: "Darwin")
    monkeypatch.setattr("src.commands.schedule.schedule_macos",
                         lambda hour, minute: calls.append((hour, minute)))
    cmd = ScheduleCommand()
    code = cmd.run(_args(time="23:50"))
    assert code == 0
    assert calls == [(23, 50)]


def test_schedule_dispatches_to_windows(monkeypatch):
    calls = []
    monkeypatch.setattr("src.commands.schedule.platform.system", lambda: "Windows")
    monkeypatch.setattr("src.commands.schedule.schedule_windows",
                         lambda hour, minute: calls.append((hour, minute)))
    cmd = ScheduleCommand()
    code = cmd.run(_args(time="06:00"))
    assert code == 0
    assert calls == [(6, 0)]


def test_schedule_unsupported_os_errors(monkeypatch, capsys):
    monkeypatch.setattr("src.commands.schedule.platform.system", lambda: "Linux")
    cmd = ScheduleCommand()
    code = cmd.run(_args(time="23:50"))
    assert code == 1
    assert "not supported" in capsys.readouterr().err


def test_schedule_subprocess_error_returns_1(monkeypatch, capsys):
    import subprocess as sp
    monkeypatch.setattr("src.commands.schedule.platform.system", lambda: "Darwin")

    def boom(hour, minute):
        raise sp.CalledProcessError(1, ["launchctl", "load"])

    monkeypatch.setattr("src.commands.schedule.schedule_macos", boom)
    cmd = ScheduleCommand()
    code = cmd.run(_args(time="23:50"))
    assert code == 1
    assert "Error" in capsys.readouterr().err


def test_unschedule_reports_removed(monkeypatch, capsys):
    monkeypatch.setattr("src.commands.schedule.platform.system", lambda: "Darwin")
    monkeypatch.setattr("src.commands.schedule.unschedule_macos", lambda: True)
    cmd = UnscheduleCommand()
    code = cmd.run(_args())
    assert code == 0
    assert "removed" in capsys.readouterr().out.lower()


def test_unschedule_reports_nothing_registered(monkeypatch, capsys):
    monkeypatch.setattr("src.commands.schedule.platform.system", lambda: "Darwin")
    monkeypatch.setattr("src.commands.schedule.unschedule_macos", lambda: False)
    cmd = UnscheduleCommand()
    code = cmd.run(_args())
    assert code == 0
    assert "no scheduled job" in capsys.readouterr().out.lower()
