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
