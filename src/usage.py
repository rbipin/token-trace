"""Immutable timestamped usage contracts and token accounting."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Literal
from .models import SessionRecord

@dataclass(frozen=True)
class UsageEvent:
    session_id: str
    source: str
    event_id: str
    model: str
    timestamp: str
    date: str
    utc_offset_minutes: int
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    reasoning_tokens: int = 0
    turn_id: str | None = None
    response_id: str | None = None
    canonical_model: str | None = None
    context: str = 'personal'
    attribution: Literal['response', 'snapshot_delta'] = 'response'

    @property
    def key(self) -> tuple[str, str, str]:
        return self.source, self.session_id, self.event_id

@dataclass(frozen=True)
class UsageCoverage:
    source: str
    session_id: str
    status: Literal['measured', 'partial', 'unavailable']
    reason: str | None = None

@dataclass(frozen=True)
class CollectionBatch:
    sessions: tuple[SessionRecord, ...] = ()
    events: tuple[UsageEvent, ...] = ()
    coverage: tuple[UsageCoverage, ...] = ()
    diagnostics: tuple[str, ...] = ()

def normalize_usage(usage: dict) -> dict[str, int]:
    fields = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
              'output_tokens', 'reasoning_output_tokens')
    values = {name: usage.get(name, 0) for name in fields}
    if any(type(value) is not int or value < 0 for value in values.values()):
        raise ValueError('usage counts must be nonnegative integers')
    uncached = values['input_tokens'] - values['cached_input_tokens'] - values['cache_write_input_tokens']
    if uncached < 0 or values['reasoning_output_tokens'] > values['output_tokens']:
        raise ValueError('usage subsets exceed their totals')
    return dict(input_tokens=uncached, output_tokens=values['output_tokens'],
        cache_read_tokens=values['cached_input_tokens'],
        cache_creation_tokens=values['cache_write_input_tokens'],
        reasoning_tokens=values['reasoning_output_tokens'])

def event_time(timestamp: str, tz: tzinfo | None = None) -> tuple[str, str, int]:
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('usage timestamp requires a timezone')
    local = dt.astimezone(tz)
    from datetime import timezone
    return (dt.astimezone(timezone.utc).isoformat(), local.date().isoformat(),
            int(local.utcoffset().total_seconds() / 60))
