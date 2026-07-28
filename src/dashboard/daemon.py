"""Daemon lifecycle management for the dashboard server.

Installs/removes a persistent background service that keeps
`tokentracer dashboard` running: a macOS launchd agent or a Windows
Scheduled Task (started immediately after creation). This is a separate job identity from the collector's
own schedule/unschedule feature (which runs `collect --lookback 1`
once daily) — it uses its own distinct job/task name so the two can
be toggled independently.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

_PLIST_LABEL = "com.ai-token-tracer.dashboard"
_TASK_NAME = "ai-token-tracer-dashboard"


def resolve_executable() -> list[str]:
    exe = shutil.which("tokentracer")
    if exe:
        return [exe]
    repo_tracker = Path(__file__).resolve().parents[2] / "tracker.py"
    return [sys.executable, str(repo_tracker)]


def install(port: int) -> bool:
    """Install and start the dashboard daemon.

    Returns True if installed/started, False if it was already running.
    """
    system = platform.system()
    if system == "Darwin":
        _install_macos(port)
        return True
    if system == "Windows":
        return _install_windows(port)
    raise RuntimeError(f"unsupported OS for dashboard daemon: {system}")


def uninstall() -> None:
    system = platform.system()
    if system == "Darwin":
        _uninstall_macos()
    elif system == "Windows":
        _uninstall_windows()
    else:
        raise RuntimeError(f"unsupported OS for dashboard daemon: {system}")


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_PLIST_LABEL}.plist"


def _install_macos(port: int) -> None:
    argv = resolve_executable() + ["dashboard", "--port", str(port)]
    log_path = Path.home() / ".tokentracer" / "dashboard.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    args_xml = "".join(f"<string>{a}</string>" for a in argv)
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n'
        f"    <key>Label</key><string>{_PLIST_LABEL}</string>\n"
        f"    <key>ProgramArguments</key><array>{args_xml}</array>\n"
        "    <key>RunAtLoad</key><true/>\n"
        "    <key>KeepAlive</key><true/>\n"
        f"    <key>StandardOutPath</key><string>{log_path}</string>\n"
        f"    <key>StandardErrorPath</key><string>{log_path}</string>\n"
        "</dict>\n</plist>\n"
    )
    path = _plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist, encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(path)], capture_output=True, text=True)
    result = subprocess.run(["launchctl", "load", str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"launchctl load failed: {result.stderr.strip()}")


def _uninstall_macos() -> None:
    path = _plist_path()
    if not path.exists():
        return
    subprocess.run(["launchctl", "unload", str(path)], capture_output=True, text=True)
    path.unlink()


def _query_windows_status() -> str | None:
    """Return the task's Status field ('Running', 'Ready', ...), or None if absent."""
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", _TASK_NAME, "/FO", "LIST"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.strip().startswith("Status:"):
            return line.split(":", 1)[1].strip()
    return ""


def _install_windows(port: int) -> bool:
    if _query_windows_status() == "Running":
        return False
    argv = resolve_executable() + ["dashboard", "--port", str(port)]
    action = " ".join(f'"{a}"' if " " in a else a for a in argv)
    result = subprocess.run(
        ["schtasks", "/Create", "/F", "/TN", _TASK_NAME,
         "/TR", action, "/SC", "ONLOGON", "/RL", "LIMITED"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"schtasks /Create failed: {result.stderr.strip()}")
    result = subprocess.run(
        ["schtasks", "/Run", "/TN", _TASK_NAME],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"schtasks /Run failed: {result.stderr.strip()}")
    return True


def _uninstall_windows() -> None:
    subprocess.run(  # stop a running dashboard first; ignore failures (may not be running)
        ["schtasks", "/End", "/TN", _TASK_NAME],
        capture_output=True, text=True,
    )
    result = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", _TASK_NAME],
        capture_output=True, text=True,
    )
    if result.returncode != 0 and "cannot find" not in result.stderr.lower():
        raise RuntimeError(f"schtasks /Delete failed: {result.stderr.strip()}")
