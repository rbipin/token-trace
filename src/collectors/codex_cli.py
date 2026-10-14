"""Read Codex active/archive rollouts without retaining conversation content."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone, tzinfo
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterator, Literal

from ..model_normalize import normalize_model
from ..models import SessionRecord
from ..repo_identity import resolve_repo_slug

AMBIGUOUS_DESCENDANT_USAGE = "ambiguous descendant cumulative usage ownership"


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
    return (dt.astimezone(timezone.utc).isoformat(), local.date().isoformat(),
            int(local.utcoffset().total_seconds() / 60))


@dataclass(frozen=True)
class CodexScan:
    """Deduplicated Codex usage for the selected rollouts, before day aggregation."""
    sessions: tuple[SessionRecord, ...] = ()   # zero-usage base per (session, model), dated on the start day
    events: tuple[UsageEvent, ...] = ()
    tools: tuple[tuple[str, str, str, str], ...] = ()  # (session_id, call_id, model, day)
    diagnostics: tuple[str, ...] = ()


class CodexCliCollector:
    source = 'codex_cli'

    def __init__(self, codex_home: Path, resolver=None, tz: tzinfo | None = None):
        self._home = Path(codex_home)
        self._resolver = resolver
        self._tz = tz

    def collect(self, since: date) -> Iterator[SessionRecord]:
        scan = self.scan(since)
        for message in scan.diagnostics:
            print(f"Warning: {message}", file=sys.stderr)
        yield from self._day_records(scan)

    def scan(self, since: date) -> CodexScan:
        events, bases, tools, diagnostics = {}, {}, {}, []
        parents = {}
        for directory in (self._home/'sessions', self._home/'archived_sessions'):
            try:
                paths = sorted(directory.rglob('*.jsonl')) if directory.exists() else []
            except OSError:
                diagnostics.append('codex_cli: cannot scan rollout directory')
                continue
            for path in paths:
                try:
                    if datetime.fromtimestamp(path.stat().st_mtime).astimezone(self._tz).date() < since:
                        continue
                    parsed = self._parse(path, parents)
                except OSError:
                    diagnostics.append('codex_cli: cannot read rollout; other sessions continue')
                    continue
                diagnostics.extend(parsed.diagnostics)
                for event in parsed.events:
                    events[event.key] = event
                for rec in parsed.sessions:
                    bases[(rec.session_id, rec.model)] = rec
                for tool in parsed.tools:
                    tools[tool[:2]] = tool
        for parent in set(parents.values()):
            if not any(e.session_id==parent and e.attribution=='response' for e in events.values()):
                events={key:e for key,e in events.items() if not (e.session_id==parent and e.attribution=='snapshot_delta')}
                diagnostics.append(f'codex_cli [{parent}]: {AMBIGUOUS_DESCENDANT_USAGE}')
        return CodexScan(tuple(bases.values()), tuple(sorted(events.values(), key=lambda e: (e.timestamp, e.key))),
                         tuple(tools.values()), tuple(dict.fromkeys(diagnostics)))

    def _rows(self, path: Path, issue):
        with path.open('rb') as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    row=json.loads(line.decode('utf-8'))
                    if not isinstance(row,dict):
                        raise ValueError('non-object entry')
                    yield row
                except (ValueError, UnicodeError):
                    issue('incomplete trailing entry; retry on next collection' if not line.endswith(b'\n') else 'malformed rollout entry')

    def _parse(self, path: Path, parents: dict | None = None) -> CodexScan:
        issues=[]
        def issue(reason):
            if reason not in issues and len(issues)<8:
                issues.append(reason)
        meta, contexts, response_format, saw_row = None, {}, False, False
        for row in self._rows(path,issue):
            saw_row=True
            if row.get('type') == 'token_usage_record':
                response_format=True
            payload=row.get('payload')
            if not isinstance(payload,dict):
                if row.get('type') in ('session_meta','turn_context','token_usage_record'):
                    issue('invalid metadata or usage payload')
                continue
            if row.get('type')=='session_meta':
                meta=payload
                if 'timestamp' not in meta:
                    meta={**meta,'timestamp':row.get('timestamp')}
            elif row.get('type')=='turn_context' and isinstance(payload.get('turn_id'),str):
                contexts[payload['turn_id']]=payload.get('model') or 'unknown'
            elif row.get('type')=='token_usage_record':
                response_format=True
        if meta is None:
            if saw_row:
                issue('missing session metadata')
            return CodexScan(diagnostics=tuple('codex_cli: '+r for r in issues))
        sid=meta.get('id')
        try:
            if not isinstance(sid,str) or not sid:
                raise ValueError('missing session identity')
            start, start_day, _ = event_time(meta.get('timestamp'),self._tz)
        except (ValueError, TypeError, AttributeError):
            return CodexScan(diagnostics=('codex_cli: invalid session identity or timestamp',))
        source=meta.get('source')
        descendant=isinstance(source,dict) and 'subagent' in source
        if descendant and parents is not None:
            details=source.get('subagent')
            if isinstance(details,dict) and isinstance(details.get('parent_thread_id'),str):
                parents[sid]=details['parent_thread_id']
        fork=bool(meta.get('forked_from_id') or meta.get('parent_thread_id') or descendant)
        cwd=meta.get('cwd')
        project=None
        if self._resolver and isinstance(cwd,str):
            name=resolve_repo_slug(cwd) or Path(cwd).name
            project=self._resolver.resolve(name,name)
        current_model, current_turn='unknown',None
        owned, tools, previous={}, {}, None
        saw_usage=False
        for row in self._rows(path,issue):
            payload=row.get('payload')
            if not isinstance(payload,dict):
                continue
            kind=row.get('type')
            if kind=='turn_context':
                current_model=payload.get('model') or 'unknown'
                current_turn=payload.get('turn_id')
                continue
            if kind=='response_item' and payload.get('type') in ('function_call','custom_tool_call'):
                call_id=payload.get('call_id')
                if isinstance(call_id,str) and call_id:
                    tools.setdefault(call_id,(current_model,self._day(row,start_day)))
                continue
            counts, attribution, rid, eid = None, 'response', None, None
            turn=payload.get('turn_id') or current_turn
            model=contexts.get(turn,current_model)
            if not isinstance(model,str):
                model='unknown'
            if kind=='token_usage_record':
                owner=payload.get('thread_id') or payload.get('session_id')
                if owner is not None and owner != sid:
                    # Copied history belongs to its source thread and is collected there.
                    continue
                if fork and owner is None:
                    issue('ambiguous descendant response ownership')
                    continue
                try:
                    if not isinstance(payload.get('usage'),dict):
                        raise ValueError('missing usage')
                    counts=normalize_usage(payload['usage'])
                    rid=payload.get('response_id')
                    if rid is not None and (not isinstance(rid,str) or not rid):
                        raise ValueError('invalid response identity')
                    if rid:
                        eid='response:'+rid
                    else:
                        eid='fingerprint:'+self._fingerprint([sid,turn,row.get('timestamp'),payload['usage']])
                        issue('usage response lacks stable response identity')
                except (ValueError,TypeError):
                    issue('invalid usage counts or response identity')
                    continue
            elif kind=='event_msg' and payload.get('type')=='token_count' and not response_format:
                info=payload.get('info')
                if not isinstance(info,dict):
                    continue
                usage=info.get('total_token_usage')
                if not isinstance(usage,dict):
                    issue('usage snapshot lacks cumulative baseline')
                    continue
                if fork:
                    issue('ambiguous descendant cumulative usage ownership')
                    continue
                try:
                    totals=normalize_usage(usage)
                    event_time(row.get('timestamp'),self._tz)
                except (ValueError,TypeError,AttributeError):
                    issue('invalid usage snapshot counts or timestamp')
                    continue
                saw_usage=True
                if info.get('accounting_reset') is True:
                    previous={k:0 for k in totals}
                if previous is None:
                    previous=totals
                    if any(totals.values()):
                        issue('usage snapshot starts with unknown baseline')
                    continue
                delta={k:totals[k]-previous[k] for k in totals}
                previous=totals
                if any(v<0 for v in delta.values()):
                    issue('usage snapshot counter decreased; baseline uncertain')
                    continue
                if not any(delta.values()):
                    continue
                if delta['reasoning_tokens'] > delta['output_tokens']:
                    issue('invalid usage snapshot delta subsets')
                    continue
                counts=delta
                attribution='snapshot_delta'
                eid='snapshot:'+self._fingerprint([sid,turn,row.get('timestamp'),totals])
            if counts is None:
                continue
            try:
                timestamp,day,offset=event_time(row.get('timestamp'),self._tz)
            except (ValueError,TypeError,AttributeError):
                issue('usage entry lacks valid timestamp')
                continue
            saw_usage=True
            event=UsageEvent(session_id=sid,source=self.source,event_id=eid,model=model,
                timestamp=timestamp,date=day,utc_offset_minutes=offset,turn_id=turn,response_id=rid,
                canonical_model=normalize_model(model,self.source),attribution=attribution,**counts)
            if eid in owned and owned[eid] != event:
                issue('conflicting duplicate usage response')
                continue
            owned[eid]=event
        models=dict.fromkeys(e.model for e in owned.values()) or {current_model:None}
        bases=tuple(SessionRecord(sid,self.source,model=model,date=start_day,start_ts=start,end_ts=start,
            project=project,canonical_model=normalize_model(model,self.source)) for model in models)
        return CodexScan(bases,tuple(owned.values()),
            tuple((sid,call_id,model,day) for call_id,(model,day) in tools.items()),
            tuple(f'codex_cli [{sid}]: {r}' for r in issues))

    @staticmethod
    def _fingerprint(value) -> str:
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def _day(self, row, fallback: str) -> str:
        try:
            return event_time(row.get('timestamp'), self._tz)[1]
        except (ValueError, TypeError, AttributeError):
            return fallback

    @classmethod
    def _day_records(cls, scan: CodexScan) -> Iterator[SessionRecord]:
        events: dict[tuple[str, str, str], list[UsageEvent]] = {}
        for e in scan.events:
            events.setdefault((e.session_id, e.model, e.date), []).append(e)
        tools = Counter((sid, model, day) for sid, _, model, day in scan.tools)
        for base in scan.sessions:
            owner = (base.session_id, base.model)
            days = sorted({d for s, m, d in [*events, *tools] if (s, m) == owner}) or [base.date]
            for day in days:
                rec = replace(base, date=day, tool_calls=tools[(*owner, day)])
                if (*owner, day) not in events:  # tool-only day: no usage timestamps
                    rec = replace(rec, start_ts=None, end_ts=None) if day != base.date else rec
                yield cls._summary(rec, events.get((*owner, day), []))

    @staticmethod
    def _summary(base, events):
        if not events:
            return base
        counts={k:sum(getattr(e,k) for e in events) for k in
                ('input_tokens','output_tokens','cache_read_tokens','cache_creation_tokens','reasoning_tokens')}
        return replace(base,**counts,turns=len(events),
            start_ts=min(e.timestamp for e in events),end_ts=max(e.timestamp for e in events),
            context_peak_tokens=max(e.input_tokens+e.cache_read_tokens+e.cache_creation_tokens+e.output_tokens for e in events))
