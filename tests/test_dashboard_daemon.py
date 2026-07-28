from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from src.dashboard import daemon


def _ok(*args, **kwargs):
    return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")


def _fail(*args, **kwargs):
    return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="boom")


def _query_running(*args, **kwargs):
    return subprocess.CompletedProcess(
        args=args, returncode=0,
        stdout="TaskName:      \\ai-token-tracer-dashboard\nStatus:        Running\n",
        stderr="")


def _query_ready(*args, **kwargs):
    return subprocess.CompletedProcess(
        args=args, returncode=0,
        stdout="TaskName:      \\ai-token-tracer-dashboard\nStatus:        Ready\n",
        stderr="")


def test_resolve_executable_prefers_path(monkeypatch):
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "/usr/local/bin/tokentracer")
    assert daemon.resolve_executable() == ["/usr/local/bin/tokentracer"]


def test_resolve_executable_falls_back_to_python(monkeypatch):
    monkeypatch.setattr(daemon.shutil, "which", lambda name: None)
    argv = daemon.resolve_executable()
    assert argv[0] == daemon.sys.executable
    assert argv[1].endswith("tracker.py")


def test_install_macos_writes_plist_and_loads(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(daemon.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "/usr/local/bin/tokentracer")
    calls = []
    with patch.object(daemon.subprocess, "run", side_effect=lambda *a, **k: (calls.append(a), _ok())[1]):
        daemon.install(8420)
    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.ai-token-tracer.dashboard.plist"
    assert plist_path.exists()
    content = plist_path.read_text()
    assert "8420" in content
    assert "<key>KeepAlive</key>" in content
    assert "<true/>" in content
    assert calls[0][0][:2] == ["launchctl", "unload"]
    assert calls[1][0][:2] == ["launchctl", "load"]


def test_install_macos_raises_on_load_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(daemon.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "/usr/local/bin/tokentracer")
    with patch.object(daemon.subprocess, "run", side_effect=[_ok(), _fail()]):
        with pytest.raises(RuntimeError, match="launchctl load failed"):
            daemon.install(8420)


def test_uninstall_macos_noop_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(daemon.Path, "home", lambda: tmp_path)
    daemon.uninstall()  # should not raise


def test_install_windows_creates_and_runs_task(monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Windows")
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "C:\\tools\\tokentracer.exe")
    calls = []
    # /Query fails (task absent), /Create ok, /Run ok
    with patch.object(daemon.subprocess, "run",
                      side_effect=lambda *a, **k: (calls.append(a[0]), [_fail(), _ok(), _ok()][len(calls) - 1])[1]):
        assert daemon.install(8420) is True
    assert calls[0][:2] == ["schtasks", "/Query"]
    assert calls[1][:3] == ["schtasks", "/Create", "/F"]
    assert calls[2][:2] == ["schtasks", "/Run"]
    assert "ai-token-tracer-dashboard" in calls[1]


def test_install_windows_already_running_skips_create(monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Windows")
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "C:\\tools\\tokentracer.exe")
    with patch.object(daemon.subprocess, "run", side_effect=[_query_running()]) as mock_run:
        assert daemon.install(8420) is False
    assert mock_run.call_count == 1  # only /Query — no /Create, no /Run


def test_install_windows_ready_task_recreated_and_run(monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Windows")
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "C:\\tools\\tokentracer.exe")
    with patch.object(daemon.subprocess, "run",
                      side_effect=[_query_ready(), _ok(), _ok()]) as mock_run:
        assert daemon.install(8420) is True
    assert mock_run.call_count == 3


def test_install_windows_run_failure_raises(monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Windows")
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "C:\\tools\\tokentracer.exe")
    with patch.object(daemon.subprocess, "run", side_effect=[_fail(), _ok(), _fail()]):
        with pytest.raises(RuntimeError, match="schtasks /Run failed"):
            daemon.install(8420)


def test_install_macos_returns_true(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(daemon.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(daemon.shutil, "which", lambda name: "/usr/local/bin/tokentracer")
    with patch.object(daemon.subprocess, "run", return_value=_ok()):
        assert daemon.install(8420) is True


def test_uninstall_windows_ends_then_deletes(monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Windows")
    calls = []
    with patch.object(daemon.subprocess, "run",
                      side_effect=lambda *a, **k: (calls.append(a[0]), _ok())[1]):
        daemon.uninstall()
    assert calls[0][:2] == ["schtasks", "/End"]
    assert calls[1][:3] == ["schtasks", "/Delete", "/F"]


def test_uninstall_windows_ignores_end_failure(monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Windows")
    with patch.object(daemon.subprocess, "run", side_effect=[_fail(), _ok()]):
        daemon.uninstall()  # should not raise


def test_install_unsupported_os_raises(monkeypatch):
    monkeypatch.setattr(daemon.platform, "system", lambda: "Linux")
    with pytest.raises(RuntimeError, match="unsupported OS"):
        daemon.install(8420)
