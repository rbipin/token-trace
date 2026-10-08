"""Read Codex active/archive rollouts without retaining conversation content."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, tzinfo
import hashlib
import json
from pathlib import Path
from typing import Iterator

from ..model_normalize import normalize_model
from ..models import SessionRecord
from ..repo_identity import resolve_repo_slug
from ..usage import AMBIGUOUS_DESCENDANT_USAGE, CollectionBatch, UsageCoverage, UsageEvent, event_time, normalize_usage


class CodexCliCollector:
    source = 'codex_cli'

    def __init__(self, codex_home: Path, resolver=None, tz: tzinfo | None = None):
        self._home = Path(codex_home)
        self._resolver = resolver
        self._tz = tz

    def collect(self, since: date) -> Iterator[SessionRecord]:
        yield from self.collect_batch(since).sessions

    def collect_batch(self, since: date) -> CollectionBatch:
        events, summaries, coverages, diagnostics = {}, {}, {}, []
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
                    batch = self._parse(path, parents)
                except OSError:
                    diagnostics.append('codex_cli: cannot read rollout; other sessions continue')
                    continue
                diagnostics.extend(batch.diagnostics)
                for event in batch.events:
                    events[event.key] = event
                for rec in batch.sessions:
                    summaries[rec.key] = rec
                for coverage in batch.coverage:
                    key=(coverage.source,coverage.session_id)
                    previous=coverages.get(key)
                    if previous is None or {'unavailable':0,'partial':1,'measured':2}[coverage.status] > {'unavailable':0,'partial':1,'measured':2}[previous.status]:
                        coverages[key]=coverage
        for parent in set(parents.values()):
            if any(e.session_id==parent and e.attribution=='snapshot_delta' for e in events.values()):
                events={key:e for key,e in events.items() if not (e.session_id==parent and e.attribution=='snapshot_delta')}
                coverages[(self.source,parent)]=UsageCoverage(self.source,parent,'partial',AMBIGUOUS_DESCENDANT_USAGE)
                diagnostics.append(f'codex_cli [{parent}]: {AMBIGUOUS_DESCENDANT_USAGE}')
                for key,rec in list(summaries.items()):
                    if rec.session_id==parent:
                        summaries[key]=replace(rec,input_tokens=0,output_tokens=0,cache_read_tokens=0,
                            cache_creation_tokens=0,reasoning_tokens=0,turns=0,context_peak_tokens=0)
        # Active/archive duplicate copies may differ in completeness; totals are from the deduplicated events.
        for key,rec in list(summaries.items()):
            owned=[e for e in events.values() if (e.session_id,e.source,e.model)==key]
            if owned:
                summaries[key]=self._summary(rec,owned)
        return CollectionBatch(tuple(summaries.values()),tuple(sorted(events.values(),key=lambda e:(e.timestamp,e.key))),
                               tuple(coverages.values()),tuple(dict.fromkeys(diagnostics)))

    def _rows(self, path: Path, issue):
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    row=json.loads(line)
                    if not isinstance(row,dict):
                        raise ValueError('non-object entry')
                    yield row
                except (ValueError, UnicodeError):
                    issue('incomplete trailing entry; retry on next collection' if not line.endswith('\n') else 'malformed rollout entry')

    def _parse(self, path: Path, parents: dict | None = None) -> CollectionBatch:
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
            return CollectionBatch(diagnostics=tuple('codex_cli: '+r for r in issues))
        sid=meta.get('id')
        try:
            if not isinstance(sid,str) or not sid:
                raise ValueError('missing session identity')
            start, start_day, _ = event_time(meta.get('timestamp'),self._tz)
        except (ValueError, TypeError, AttributeError):
            return CollectionBatch(diagnostics=('codex_cli: invalid session identity or timestamp',))
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
                    tools.setdefault(call_id,current_model)
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
        status='partial' if issues else ('measured' if saw_usage else 'unavailable')
        reason='; '.join(issues) if issues else ('no recorded usage' if status=='unavailable' else None)
        models=dict.fromkeys(e.model for e in owned.values()) or {current_model:None}
        records=[]
        for model in models:
            base=SessionRecord(sid,self.source,model=model,date=start_day,start_ts=start,end_ts=start,
                project=project,tool_calls=sum(m==model for m in tools.values()),canonical_model=normalize_model(model,self.source))
            records.append(self._summary(base,[e for e in owned.values() if e.model==model]))
        return CollectionBatch(tuple(records),tuple(owned.values()),(UsageCoverage(self.source,sid,status,reason),),
            tuple(f'codex_cli [{sid}]: {r}' for r in issues))

    @staticmethod
    def _fingerprint(value) -> str:
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    @staticmethod
    def _summary(base, events):
        if not events:
            return base
        counts={k:sum(getattr(e,k) for e in events) for k in
                ('input_tokens','output_tokens','cache_read_tokens','cache_creation_tokens','reasoning_tokens')}
        return replace(base,**counts,turns=len(events),end_ts=max(e.timestamp for e in events),
            context_peak_tokens=max(e.input_tokens+e.cache_read_tokens+e.cache_creation_tokens+e.output_tokens for e in events))
