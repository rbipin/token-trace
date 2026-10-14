from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterator

from .base import to_date, to_local_iso
from ..models import SessionRecord, UNKNOWN_MODEL
from ..repo_identity import resolve_repo_slug

_COUNTERS = ("turns", "tool_calls", "input_tokens", "output_tokens",
             "cache_creation_tokens", "cache_read_tokens", "context_peak_tokens")


class ClaudeCliCollector:
    """Yields one SessionRecord per (conversation file, local day) with assistant activity."""

    source = "claude_cli"

    def __init__(self, projects_dir: Path, resolver=None) -> None:
        """Args:
            projects_dir: Root of ~/.claude/projects.
            resolver: Optional ProjectNameResolver; when None, records carry
                no project identity.
        """
        self._dir = projects_dir
        self._resolver = resolver

    def collect(self, since: date) -> Iterator[SessionRecord]:
        for jsonl_path in self._dir.rglob("*.jsonl"):
            # Files untouched since the window hold no recent activity. A file
            # modified since is re-emitted in full, one record per active day.
            try:
                mtime_date = date.fromtimestamp(jsonl_path.stat().st_mtime)
            except OSError:
                continue
            if mtime_date < since:
                continue
            yield from self._parse_session(jsonl_path)

    def _parse_session(self, path: Path) -> list[SessionRecord]:
        session_id = path.stem
        model = UNKNOWN_MODEL
        cwd_seen: str | None = None
        start_ts: str | None = None
        bounds: dict[str, list[str]] = {}        # day -> [first_ts, last_ts]
        days: dict[str | None, dict] = {}        # day (None = untimed) -> counters

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts = entry.get("timestamp")
            entry_day = to_date(ts) if ts else None
            day = entry_day.isoformat() if entry_day else None
            if ts:
                if start_ts is None or ts < start_ts:
                    start_ts = ts
                if day:
                    span = bounds.setdefault(day, [ts, ts])
                    span[0], span[1] = min(span[0], ts), max(span[1], ts)

            if cwd_seen is None and self._resolver is not None:
                cwd = entry.get("cwd")
                if cwd:
                    cwd_seen = cwd

            if entry.get("type") != "assistant":
                continue

            msg = entry.get("message") or {}
            if model == UNKNOWN_MODEL and msg.get("model"):
                model = msg["model"]
            usage = msg.get("usage") or {}
            counts = days.setdefault(day, dict.fromkeys(_COUNTERS, 0))
            counts["turns"] += 1
            counts["input_tokens"] += usage.get("input_tokens", 0)
            counts["output_tokens"] += usage.get("output_tokens", 0)
            counts["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
            counts["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
            footprint = (
                usage.get("input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
                + usage.get("output_tokens", 0)
            )
            counts["context_peak_tokens"] = max(counts["context_peak_tokens"], footprint)
            content = msg.get("content") or []
            if isinstance(content, list):
                counts["tool_calls"] += sum(
                    1 for block in content
                    if isinstance(block, dict) and block.get("type") == "tool_use"
                )

        start_day = to_date(start_ts) if start_ts else None
        start_day_str = start_day.isoformat() if start_day else date.today().isoformat()
        # Untimed assistant usage, or a session without any, lands on the start day.
        untimed = days.pop(None, None)
        if untimed or not days:
            merged = days.setdefault(start_day_str, dict.fromkeys(_COUNTERS, 0))
            for name, value in (untimed or {}).items():
                merged[name] = (max(merged[name], value) if name == "context_peak_tokens"
                                else merged[name] + value)

        project: str | None = None
        if self._resolver is not None and cwd_seen:
            project_key = resolve_repo_slug(cwd_seen) or Path(cwd_seen).name or None
            project = self._resolver.resolve(project_key, project_key)

        return [
            SessionRecord(
                session_id=session_id,
                source=self.source,
                model=model,
                date=day,
                start_ts=to_local_iso(bounds[day][0]) if day in bounds else None,
                end_ts=to_local_iso(bounds[day][1]) if day in bounds else None,
                project=project,
                **counts,
            )
            for day, counts in sorted(days.items())
        ]
