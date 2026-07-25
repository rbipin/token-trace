"""Platform-native scheduling helpers for the daily collect job.

Shared by src/commands/schedule.py's ScheduleCommand/UnscheduleCommand.
Kept OS-agnostic here; the command layer decides which platform functions
to call based on platform.system().
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

LABEL = "com.ai-token-tracer"
TASK_NAME = "ai-token-tracer"

_TRACKER_PY_PATH = Path(__file__).resolve().parent.parent / "tracker.py"
_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
_LOG_PATH = Path.home() / ".tokentracer" / "tracker.log"

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_time(value: str) -> tuple[int, int]:
    """Parse an "HH:MM" string into (hour, minute); raises ValueError if invalid."""
    match = _TIME_RE.match(value)
    if not match:
        raise ValueError(f"invalid time {value!r}; expected HH:MM (24-hour)")
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        raise ValueError(f"invalid time {value!r}; hour must be 0-23, minute 0-59")
    return hour, minute


def resolve_executable() -> list[str]:
    """Return the argv prefix to invoke tokentracer.

    Prefers the packaged console script on PATH; falls back to running
    tracker.py from this repo checkout with the current interpreter.
    """
    on_path = shutil.which("tokentracer")
    if on_path:
        return [on_path]
    if not _TRACKER_PY_PATH.exists():
        raise FileNotFoundError(
            f"neither 'tokentracer' on PATH nor tracker.py at {_TRACKER_PY_PATH}"
        )
    return [sys.executable, str(_TRACKER_PY_PATH)]


_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
{prog_args}
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>{log_path}</string>

    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""


def build_plist(hour: int, minute: int, prog_args: list[str]) -> str:
    """Render the launchd plist XML for the given time and program arguments."""
    args_xml = "\n".join(f"        <string>{arg}</string>" for arg in prog_args)
    return _PLIST_TEMPLATE.format(
        label=LABEL, prog_args=args_xml, hour=hour, minute=minute, log_path=_LOG_PATH
    )


def schedule_macos(hour: int, minute: int) -> None:
    """Register (or silently replace) the daily launchd job on macOS."""
    prog_args = resolve_executable() + ["collect", "--lookback", "1"]
    plist_xml = build_plist(hour, minute, prog_args)
    _PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "unload", str(_PLIST_PATH)], capture_output=True)
    _PLIST_PATH.write_text(plist_xml, encoding="utf-8")
    subprocess.run(["launchctl", "load", str(_PLIST_PATH)], check=True, capture_output=True)


def unschedule_macos() -> bool:
    """Remove the daily launchd job on macOS. Returns False if none was registered."""
    if not _PLIST_PATH.exists():
        return False
    subprocess.run(["launchctl", "unload", str(_PLIST_PATH)], capture_output=True)
    _PLIST_PATH.unlink()
    return True


def schedule_windows(hour: int, minute: int) -> None:
    """Register (or silently replace, via /F) the daily scheduled task on Windows."""
    prog_args = resolve_executable() + ["collect", "--lookback", "1"]
    exe, *rest = prog_args
    command = " ".join([f'"{exe}"', *rest])
    subprocess.run(
        [
            "schtasks", "/Create", "/F",
            "/SC", "DAILY",
            "/TN", TASK_NAME,
            "/TR", command,
            "/ST", f"{hour:02d}:{minute:02d}",
        ],
        check=True,
        capture_output=True,
    )


def unschedule_windows() -> bool:
    """Remove the daily scheduled task on Windows. Returns False if none was registered."""
    query = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME], capture_output=True
    )
    if query.returncode != 0:
        return False
    subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], check=True, capture_output=True)
    return True
