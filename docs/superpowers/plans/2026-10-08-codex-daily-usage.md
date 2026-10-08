# Codex Daily Usage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect Codex usage by session and model, attribute tokens to their actual local usage days, and preserve idempotent collection, reporting, and remote sync.

**Architecture:** Keep existing lifetime `SessionRecord` summaries and add immutable timestamped usage events through an optional batch-collector interface. Commit events, coverage markers, and summaries together; expose daily aggregates through SQLite views with an exclusive legacy fallback. Normalize models through the existing function and preserve the session-only extension contracts.

**Tech Stack:** Python 3.11+, `dataclasses`, `datetime`, `zoneinfo`, `sqlite3`, `json`, `hashlib`, `pytest`; existing React/Vite dashboard and optional Supabase client.

**Spec:** `docs/superpowers/specs/2026-10-08-codex-daily-usage-design.md`

## Global Constraints

- Python 3.11+; standard library only at runtime except the existing optional Supabase dependency.
- Preserve `(session_id, source, model)` as the session primary key; canonical names never form identity keys.
- New Codex source identifier: `codex_cli`; display label: `Codex`, covering locally persisted CLI and editor sessions.
- Keep session records and usage events frozen; transform them with `dataclasses.replace()`.
- Do not persist or sync prompts, tool arguments, tool output, reasoning text, or raw project paths.
- Existing session-only third-party collectors and stores must continue to work.
- Store UTC event timestamps and the collection machine's local day and UTC offset at the event instant; reimports of an existing event preserve its original day assignment.
- Historical session-only rows remain identifiable as legacy attribution; never describe their start-date allocation as measured daily usage.
- Planning creates documentation only; implementation, installation, live database writes, remote schema changes, and publishing are outside this request.

## Required execution order

Always use the writing-plans skill's usual test-first sequence for implementation plans: **write a failing test → run it and verify the expected failure → implement the smallest change → run focused tests and verify they pass → commit code and tests together**. This instruction supersedes the earlier tests-at-the-end order, including the order recorded in the linked design spec.

Tasks 1–6 create and update tests alongside their runtime changes. Repeat the sequence for each additional behavior in a task; do not implement the whole task before adding its regression cases. An unexpected import, fixture, or environment error is not proof of the intended behavioral failure: fix unrelated setup problems and rerun. A missing new module/API is an expected initial failure only for the task introducing it. Finish each task with its new tests and relevant existing regressions passing before proceeding.

Task 7 adds the end-to-end integration regression first, reproduces any remaining integration defect before fixing it, and verifies the complete scenario matrix. It then updates `CLAUDE.md`, `README.md`, architecture documentation, and package metadata to describe verified behavior. Documentation remains last; tests do not. Planning itself changes documentation only and does not execute this implementation sequence.

## Review Focus

- A timezone change between imports must not shift an existing event's date; Tasks 1 and 2 pin historical offsets and persisted date assignment before implementation.
- A malformed live JSONL tail must not erase previous events or stop other sessions; Task 3 tests partial lines and completed appends before changing the parser.
- A session resumed outside the creation-date lookback must update; Task 3 tests old creation with recent modification before implementing activity selection.
- Forked history and subagent counters must not duplicate consumed tokens; Task 3 tests ownership and inherited history before implementing deduplication and partial coverage.
- Remote event failure after successful session sync must remain retryable; Task 6 tests independent acknowledgments and corrections before implementing retry behavior.

## File structure and task boundaries

| Files | Responsibility |
|---|---|
| `src/usage.py` (new) | Frozen event/batch/coverage types, token normalization, timestamp conversion |
| `src/stores/sqlite_usage.py` (new) | Event schema, atomic batch persistence, daily/reporting views, event acknowledgments |
| `src/stores/sqlite.py` | Invoke additive migration and delegate event operations |
| `src/collectors/codex_cli.py` (new) | Read rollouts and produce summaries, events, coverage, diagnostics |
| `src/collectors/base.py`, `src/collectors/__init__.py` | Optional batch protocol and collector export |
| `src/config.py`, `src/commands/collect.py` | Codex path and pipeline registration |
| `src/pipeline.py`, `src/middleware/model_normalize.py` | Preserve old interfaces and process event batches |
| `src/dashboard/queries.py`, `src/report.py`, `src/commands/report.py` | Period usage and lifetime metadata semantics |
| `src/stores/__init__.py`, `src/stores/supabase.py`, `src/commands/common.py` | Optional remote event capability and retries |
| `frontend/src/theme.js`, `frontend/src/components/ContextBreakdown.jsx`, `frontend/src/pages/TokensPage.jsx` | Codex label and attribution disclosure |
| `docs/migrations/2026-10-08-usage-events.sql` (new) | Reviewable remote additive schema migration |
| `tests/usage_helpers.py` (new) and new focused tests | Synthetic records, source fixtures, behavior verification |
| `README.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, `pyproject.toml` | Supported source, architecture, scope, and import/sync documentation |

These are one dependent feature, not independent redesigns: correct daily reports depend on the ledger and correct synchronization depends on its identity contract. Claude/Copilot event conversion and a live app-server integration are separate projects.

---

### Task 1: Define immutable usage contracts and accounting

**Files:** Create `src/usage.py`, `tests/usage_helpers.py`, `tests/test_usage.py`.

**Interfaces:** Produces `UsageEvent`, `UsageCoverage`, `CollectionBatch`, `normalize_usage(usage: dict) -> dict[str, int]`, and `event_time(timestamp: str, tz: tzinfo | None = None) -> tuple[str, str, int]`.

- [x] **Step 1: Write failing accounting and timezone tests in `tests/test_usage.py`.**

```python
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from src.usage import normalize_usage, event_time

def test_cache_and_reasoning_are_subsets():
    counts = normalize_usage(dict(input_tokens=1000, cached_input_tokens=600,
        cache_write_input_tokens=100, output_tokens=200, reasoning_output_tokens=80))
    assert counts == dict(input_tokens=300, cache_read_tokens=600,
        cache_creation_tokens=100, output_tokens=200, reasoning_tokens=80)
    assert sum(counts[k] for k in (
        'input_tokens', 'cache_read_tokens', 'cache_creation_tokens', 'output_tokens')) == 1200

@pytest.mark.parametrize('value', [-1, True, 1.5, '100'])
def test_invalid_counts_are_rejected(value):
    with pytest.raises(ValueError):
        normalize_usage({'input_tokens': value})

def test_local_midnight_and_dst_offsets():
    tz = ZoneInfo('America/Detroit')
    assert event_time('2026-10-09T03:59:59Z', tz)[1] == '2026-10-08'
    assert event_time('2026-10-09T04:00:00Z', tz)[1] == '2026-10-09'
    before = event_time('2026-11-01T05:30:00Z', tz)
    after = event_time('2026-11-01T06:30:00Z', tz)
    assert before[1] == after[1] == '2026-11-01'
    assert (before[2], after[2]) == (-240, -300)
```

- [x] **Step 2: Run the tests and verify the expected failure.**

Run: `.venv/bin/python -m pytest tests/test_usage.py -v`
Expected: FAIL because `src.usage` does not exist yet.
- [x] **Step 3: Implement the contracts and conversion functions.**

```python
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
```

Create this synthetic event helper in Task 1 for later tasks, with no real user data. In Steps 1–2, keep its new-module import inside the function so the helper itself can load before `src.usage` exists:

```python
# tests/usage_helpers.py
def event(sid='s1', eid='r1', day='2026-10-08', tokens=100, model='gpt-5.3-codex'):
    from src.usage import UsageEvent
    return UsageEvent(session_id=sid, source='codex_cli', event_id=eid, model=model,
        timestamp=f'{day}T12:00:00+00:00', date=day, utc_offset_minutes=0,
        input_tokens=tokens, response_id=eid)
```

- [x] **Step 4: Run tests and verify they pass.** Run `.venv/bin/python -m pytest tests/test_usage.py -v`; expected: PASS. Repeat Steps 1–4 for cache subsets exceeding input, reasoning exceeding output, timezone-free timestamps, immutability, and raw identity unchanged by canonical aliases.
- [x] **Step 5: Commit** the runtime file, synthetic helper, and passing tests together with `feat: define timestamped usage contracts`.

### Task 2: Persist atomic batches and expose exclusive daily views

**Files:** Create `src/stores/sqlite_usage.py`, `tests/test_sqlite_usage.py`; modify `src/stores/sqlite.py`.

**Interfaces:** `SqliteStore.upsert_batch(batch: CollectionBatch) -> int` returns session rows written. `SqliteStore.unsynced_events_for(store_name: str) -> list[UsageEvent]`; `SqliteStore.mark_events_synced(events: list[UsageEvent], store_name: str) -> None`. Existing `upsert` remains supported. Produces `usage_daily` and `reporting_usage` views.

- [x] **Step 1: Write failing batch-persistence tests in `tests/test_sqlite_usage.py`.**

```python
import sqlite3
from dataclasses import replace
from src.models import SessionRecord
from src.usage import CollectionBatch, UsageCoverage
from src.stores.sqlite import SqliteStore
from tests.usage_helpers import event

def test_daily_split_preserves_one_lifetime_summary(tmp_path):
    path = tmp_path / 'usage.db'
    store = SqliteStore(path)
    rec = SessionRecord('s1', 'codex_cli', model='gpt-5.3-codex',
                        date='2026-10-08', input_tokens=150)
    batch = CollectionBatch((rec,), (event(tokens=100),
        event(eid='r2', day='2026-10-09', tokens=50)),
        (UsageCoverage('codex_cli', 's1', 'measured'),))
    store.upsert_batch(batch)
    store.upsert_batch(batch)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
        assert conn.execute('SELECT date, input_tokens FROM usage_daily ORDER BY date').fetchall() == [
            ('2026-10-08', 100), ('2026-10-09', 50)]
        assert conn.execute('SELECT SUM(input_tokens) FROM reporting_usage').fetchone()[0] == 150

def test_reimport_preserves_original_local_date(tmp_path):
    store = SqliteStore(tmp_path / 'usage.db')
    rec = SessionRecord('s1', 'codex_cli', model='gpt-5.3-codex', date='2026-10-08')
    original = event()
    store.upsert_batch(CollectionBatch((rec,), (original,)))
    moved = replace(original, date='2026-10-09', utc_offset_minutes=540)
    store.upsert_batch(CollectionBatch((rec,), (moved,)))
    assert store.unsynced_events_for('remote')[0].date == '2026-10-08'
```

- [x] **Step 2: Run the tests and verify the expected failure.**

Run: `.venv/bin/python -m pytest tests/test_sqlite_usage.py -v`
Expected: FAIL because `SqliteStore.upsert_batch` does not exist yet; Task 1 imports must succeed.
- [x] **Step 3: Add additive migration DDL in `sqlite_usage.py`.** Use the following keys and indexes; include all `UsageEvent` fields as typed columns and never drop existing rows.

```sql
CREATE TABLE IF NOT EXISTS usage_coverage (
    source TEXT NOT NULL, session_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('measured','partial','unavailable')),
    reason TEXT,
    PRIMARY KEY(source, session_id)
);
CREATE TABLE IF NOT EXISTS usage_event_sync_log (
    source TEXT NOT NULL, session_id TEXT NOT NULL, event_id TEXT NOT NULL,
    store_name TEXT NOT NULL, synced_at TEXT NOT NULL,
    PRIMARY KEY(source, session_id, event_id, store_name)
);
CREATE INDEX IF NOT EXISTS usage_events_date ON usage_events(date);
CREATE INDEX IF NOT EXISTS usage_events_session ON usage_events(source,session_id,model);
```

Extract the existing session row write loop into `_upsert_sessions(conn, records) -> int`, preserving its correction/sync behavior. Both `upsert()` and `upsert_batch()` call it under a single connection transaction. Upsert events with `ON CONFLICT(source,session_id,event_id) DO UPDATE`; update metrics, model, canonical model, context and timestamp but preserve stored `date` and `utc_offset_minutes`. Delete event sync markers only when persisted values actually change. Upsert coverage in the same transaction. Roll back the entire batch on storage errors.

The views must explicitly select matching column lists, not `SELECT *`:

```sql
-- usage_daily: group events by source, session_id, model, date;
-- SUM each token field, COUNT(*) AS turns (model response count),
-- 0 AS tool_calls, MAX(inclusive input + output) AS context_peak_tokens.
-- Join sessions on all three session-key columns for project/context/canonical metadata.
-- MIN/MAX event timestamps are period usage bounds; retain session bounds separately.
-- Include coverage.status and event attribution quality.

-- reporting_usage's legacy branch must use this exclusion:
SELECT s.session_id, s.source, s.model, s.date
FROM sessions s
WHERE NOT EXISTS (
    SELECT 1 FROM usage_coverage c
    WHERE c.source = s.source AND c.session_id = s.session_id
);
```

Complete the two view definitions with identical projected token/metadata columns and `UNION ALL`. An event-aware session never contributes its lifetime summary to that union, even when coverage is partial or unavailable.

- [x] **Step 4: Run tests and verify they pass.** Run `.venv/bin/python -m pytest tests/test_sqlite_usage.py tests/test_sqlite_resync.py tests/test_store_report.py -q`; expected: PASS. Repeat Steps 1–4 for preexisting-row migration, mixed-attribution, partial/unavailable coverage, correction/acknowledgment, and atomic-rollback tests.
- [x] **Step 5: Commit runtime changes and passing tests together** with `feat: add atomic usage ledger and daily reporting views`.

### Task 3: Parse Codex rollouts with deterministic event ownership

**Files:** Create `src/collectors/codex_cli.py`, `tests/test_codex_cli_collector.py`; modify `src/collectors/base.py`, `src/collectors/__init__.py`.

**Interfaces:** `CodexCliCollector(codex_home: Path, resolver=None, tz: tzinfo | None = None)`; `collect_batch(since: date) -> CollectionBatch`; compatibility `collect(since: date) -> Iterator[SessionRecord]`. Optional `BatchActivityCollector` protocol exposes `source` and `collect_batch`.

- [x] **Step 1: Write the synthetic source builders and failing two-day test in `tests/test_codex_cli_collector.py`.**

```python
import json
from datetime import date
from zoneinfo import ZoneInfo
from src.collectors.codex_cli import CodexCliCollector

def write_rollout(root, rows, name='rollout.jsonl'):
    path = root / 'sessions' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
    return path

def usage_row(rid, ts, tokens):
    return dict(type='token_usage_record', timestamp=ts, payload=dict(
        session_id='s1', thread_id='s1', turn_id='t1', response_id=rid,
        usage=dict(input_tokens=tokens, output_tokens=0)))

def test_resumed_session_splits_usage_across_days(tmp_path):
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-09-01T12:00:00Z', cwd='/synthetic/project', source='vscode')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-09T03:59:59Z', 100),
        usage_row('r2', '2026-10-09T04:00:00Z', 50)]
    write_rollout(tmp_path, rows)
    batch = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect_batch(date(2026,10,8))
    assert [(e.date, e.input_tokens) for e in batch.events] == [('2026-10-08',100),('2026-10-09',50)]
    assert batch.sessions[0].session_id == 's1'
    assert batch.sessions[0].input_tokens == 150
```

Add these Review Focus regressions in the same file before implementing the corresponding parser behavior:

```python
def test_recent_activity_selects_old_session(tmp_path):
    import os
    from datetime import datetime, timezone
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-09-01T12:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-08T12:00:00Z', 100)]
    path = write_rollout(tmp_path, rows)
    modified = datetime(2026, 10, 8, 16, tzinfo=timezone.utc).timestamp()
    os.utime(path, (modified, modified))
    batch = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect_batch(date(2026,10,8))
    assert len(batch.sessions) == 1
    assert sum(e.input_tokens for e in batch.events) == 100


def test_partial_tail_completed_on_next_import(tmp_path):
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-10-08T12:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-08T12:01:00Z', 100)]
    path = write_rollout(tmp_path, rows)
    final = json.dumps(usage_row('r2', '2026-10-08T12:02:00Z', 50))
    with path.open('a', encoding='utf-8') as stream:
        stream.write(final[:len(final)//2])
    collector = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit'))
    before = collector.collect_batch(date(2026,10,8))
    assert [(e.response_id, e.input_tokens) for e in before.events] == [('r1',100)]
    assert before.coverage[0].status == 'partial'
    with path.open('a', encoding='utf-8') as stream:
        stream.write(final[len(final)//2:] + '\n')
    after = collector.collect_batch(date(2026,10,8))
    again = collector.collect_batch(date(2026,10,8))
    assert [(e.response_id, e.input_tokens) for e in after.events] == [('r1',100),('r2',50)]
    assert again.events == after.events


def test_fork_copied_response_retains_originating_owner(tmp_path):
    parent = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-10-08T12:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-08T12:01:00Z', 100)]
    write_rollout(tmp_path, parent, 'parent.jsonl')
    child = [dict(type='session_meta', payload=dict(id='child',
        timestamp='2026-10-08T12:02:00Z', source='cli')),
        parent[1], parent[2]]
    own = usage_row('r2', '2026-10-08T12:03:00Z', 50)
    own['payload'].update(session_id='child', thread_id='child')
    child.append(own)
    write_rollout(tmp_path, child, 'child.jsonl')
    batch = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect_batch(date(2026,10,8))
    assert sorted((e.session_id,e.response_id,e.input_tokens) for e in batch.events) == [
        ('child','r2',50), ('s1','r1',100)]
    assert sum(r.input_tokens for r in batch.sessions) == 150
```

For each new regression, run `.venv/bin/python -m pytest tests/test_codex_cli_collector.py::<test_name> -v` using its exact name above; expect the missing behavior to fail before implementing it and PASS afterward. The ownership fixture pins explicit `thread_id` behavior; add ambiguous-ownership cases with partial coverage and diagnostic assertions before enabling a less explicit source variant.

- [x] **Step 2: Run the test and verify the expected failure.**

Run: `.venv/bin/python -m pytest tests/test_codex_cli_collector.py::test_resumed_session_splits_usage_across_days -v`
Expected: FAIL because `src.collectors.codex_cli` does not exist yet.
- [x] **Step 3: Implement two-pass parsing without retaining conversation text.** First pass identifies session/turn metadata and whether per-response usage exists; second pass streams accepted accounting entries. Scan both `sessions` and `archived_sessions`; ignore missing directories. Select files by local mtime/activity date and parse the selected files in full. Resolve project through the existing resolver; store neither cwd nor message text.

Use this event construction after validating ownership and usage:

```python
from src.model_normalize import normalize_model
from src.usage import UsageEvent, event_time, normalize_usage

def response_event(session_id, model, entry, tz):
    payload = entry['payload']
    response_id = payload['response_id']
    timestamp, day, offset = event_time(entry['timestamp'], tz)
    return UsageEvent(session_id=session_id, source='codex_cli',
        event_id='response:' + response_id, response_id=response_id,
        turn_id=payload.get('turn_id'), model=model,
        canonical_model=normalize_model(model, 'codex_cli'),
        timestamp=timestamp, date=day, utc_offset_minutes=offset,
        **normalize_usage(payload['usage']))
```

Prefer metadata/turn ownership, and deduplicate response IDs within each originating session. Group accepted events by raw model to build lifetime records. If a per-response entry lacks response ID, use a SHA-256 fingerprint of canonical JSON containing owner session, turn ID, timestamp, and usage; label coverage partial because identity is weaker.

For fallback snapshots use component differences from the preceding cumulative snapshot, not `last_token_usage` sums. Event IDs are hashes of session ID, turn ID, timestamp, and cumulative counters; do not hash unstable filename/line offsets. Ignore repeated counters. A counter decrease or inherited/ambiguous initial baseline produces partial coverage and no fabricated reset delta. An explicit fresh-accounting boundary permits a new zero baseline. Always preserve previous accepted events.

Deduplicate `function_call` and `custom_tool_call` items by call ID. Count accepted response events as model requests; do not call that count user turns in new copy. Derive footprint using original inclusive input plus output. Missing usage creates metadata plus unavailable coverage. Parsing errors produce bounded session diagnostics and partial coverage. A truncated final line produces no diagnostic claiming permanent corruption; retry it on the next run.

- [x] **Step 4: Run tests and verify they pass.** Run `.venv/bin/python -m pytest tests/test_codex_cli_collector.py tests/test_claude_cli_collector.py tests/test_cli_collector.py -q`; expected: PASS. Repeat Steps 1–4 for the collector scenario checklist using `write_rollout` and `usage_row`: both formats coexisting count once; identical response duplicated; same file moved to archive; model change between two turn contexts; malformed scalar JSON; partial tail then valid append; missing usage; subset validation failure; repeated fallback counters; counter reset with and without explicit boundary; context compaction preserving earlier usage; root/child ownership; copied fork response IDs. Where fixtures cannot establish owner/aggregation, assert partial coverage and a diagnostic, never a guessed total.
- [x] **Step 5: Commit runtime changes and passing collector tests together** with `feat: collect Codex responses and legacy usage deltas`.

### Task 4: Integrate batches without breaking session-only plugins

**Files:** Modify `src/config.py`, `src/commands/collect.py`, `src/pipeline.py`, `src/middleware/model_normalize.py`; test `tests/test_pipeline.py`, `tests/test_pipeline_multi_store.py`, `tests/test_config.py`, `tests/test_tracker_cli.py`, `tests/test_middleware_model_normalize.py`.

**Interfaces:** New `Paths.codex_home`; `ModelNormalizeMiddleware.process_events(events: list[UsageEvent]) -> list[UsageEvent]`. Collectors with `collect_batch` produce batches; others are wrapped using their existing `collect`. SQLite receives the combined batch once, atomically; other stores still receive `upsert(sessions)`.

- [x] **Step 1: Write the failing mixed-collector test in `tests/test_pipeline.py`.**

```python
from datetime import date
from src.models import SessionRecord
from src.usage import CollectionBatch, UsageCoverage
from src.pipeline import TrackerPipeline
from src.stores.sqlite import SqliteStore
from tests.usage_helpers import event

def test_batch_and_legacy_collectors_share_pipeline(tmp_path):
    class Legacy:
        source = 'claude_cli'
        def collect(self, since):
            return [SessionRecord('legacy','claude_cli', date='2026-10-08', input_tokens=20)]
    class Codex:
        source = 'codex_cli'
        def collect_batch(self, since):
            rec = SessionRecord('s1','codex_cli', model='gpt-5.3-codex',
                                date='2026-10-08', input_tokens=100)
            return CollectionBatch((rec,), (event(),),
                (UsageCoverage('codex_cli','s1','measured'),))
    store = SqliteStore(tmp_path / 'usage.db')
    result = TrackerPipeline().add(Legacy()).add(Codex()).since(date(2026,10,8)).stores(store).run()
    assert result.records_written == 2
    assert len(store.unsynced_events_for('remote')) == 1
```

- [x] **Step 2: Run the test and verify the expected failure.**

Run: `.venv/bin/python -m pytest tests/test_pipeline.py::test_batch_and_legacy_collectors_share_pipeline -v`
Expected: FAIL because the pipeline cannot consume the Codex batch collector or does not persist its events.
- [x] **Step 3: Register paths and collector; dispatch batches by capability.**

```python
# New Paths field; explicit injected Paths values retain precedence over environment defaults.
codex_home: Path = field(default_factory=lambda:
    Path(os.environ.get('CODEX_HOME') or str(Path.home() / '.codex')).expanduser())

# Collector dispatch inside the existing concurrent collection function:
if callable(getattr(collector, 'collect_batch', None)):
    batch = collector.collect_batch(self._since)
else:
    batch = CollectionBatch(sessions=tuple(collector.collect(self._since)))

# New method on ModelNormalizeMiddleware:
def process_events(self, events):
    return [replace(e, canonical_model=normalize_model(e.model, e.source)) for e in events]
```

Merge session rows with existing `merge_records`; merge events by `UsageEvent.key`. Stamp context on both. Apply existing middleware to sessions and call optional `process_events` for events. For the built-in SQLite sink use `upsert_batch`; a legacy custom primary store receives summaries and an event-capability warning. Aggregate batch diagnostics into the existing error output. Extend `RunResult` additively with `events_written: int = 0`, and report session and event counts without changing existing flags. Source registration occurs in `_build_pipeline`, not `tracker.py`.

- [x] **Step 4: Run tests and verify they pass; repeat Steps 1–4 for `CODEX_HOME`, missing directories, custom injected paths, legacy collector/store contracts, masked project identity, context stamping, normalization of unknown and dated model names, collector failure isolation, and unchanged schedule lookback.** Run `.venv/bin/python -m pytest tests/test_pipeline.py tests/test_pipeline_multi_store.py tests/test_config.py tests/test_tracker_cli.py tests/test_middleware_model_normalize.py tests/test_context.py tests/test_project_resolver.py -q`; expected: PASS.
- [x] **Step 5: Commit runtime changes and passing tests together** with `feat: wire Codex batches into collection pipeline`.

### Task 5: Report actual usage dates and disclose legacy attribution

**Files:** Modify `src/dashboard/queries.py`, `src/report.py`, `src/commands/report.py`, `frontend/src/theme.js`, `frontend/src/components/ContextBreakdown.jsx`, `frontend/src/pages/TokensPage.jsx`; create `tests/test_daily_reporting.py`; modify `tests/test_dashboard_queries.py`, `tests/test_store_report.py`.

**Interfaces:** Existing dashboard function signatures and existing CLI flags remain. Summary responses gain `attribution` with `legacy_tokens`, `partial_session_count`, `unavailable_session_count`. Daily/period token amounts use `reporting_usage`; lifetime activity is explicitly labeled in session views.

- [x] **Step 1: Write the failing period-attribution test in `tests/test_daily_reporting.py`.**

```python
import sqlite3
from src.dashboard import queries
from src.models import SessionRecord
from src.stores.sqlite import SqliteStore
from src.usage import CollectionBatch, UsageCoverage
from tests.usage_helpers import event

def test_period_totals_do_not_repeat_session_lifetime(tmp_path):
    path = tmp_path / 'usage.db'
    store = SqliteStore(path)
    rec = SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08',input_tokens=150)
    store.upsert_batch(CollectionBatch((rec,), (event(tokens=100),
        event(eid='r2',day='2026-10-09',tokens=50)),
        (UsageCoverage('codex_cli','s1','measured'),)))
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        first = queries.summary(conn,'custom','2026-10-08','2026-10-08')
        second = queries.summary(conn,'custom','2026-10-09','2026-10-09')
        both = queries.summary(conn,'all')
    assert (first['total_tokens'],second['total_tokens'],both['total_tokens']) == (100,50,150)
    assert both['session_count'] == 1
```

- [x] **Step 2: Run the test and verify the expected failure.**

Run: `.venv/bin/python -m pytest tests/test_daily_reporting.py::test_period_totals_do_not_repeat_session_lifetime -v`
Expected: FAIL because summaries still allocate the lifetime 150 tokens to the session start date instead of returning `(100, 50, 150)`.
- [x] **Step 3: Switch all usage queries consistently.** Dashboard `summary`, `_rolling_stats`, `heatmap`, `trend`, `projects`, and `project_detail` must use `reporting_usage`. Session counts use a grouped subquery with `GROUP BY source,session_id`, not string concatenation or `COUNT(*)`. Derive active days from usage dates. Preserve canonical model filters, source/context/project grouping and local project display aliases. Build rolling-query parameters independently from period bounds, avoiding accidental reuse of custom-date parameters.

Update CLI strategies: period rollups and project views aggregate daily rows; session views group the selected usage back to `(session_id,source,model)` and join lifetime metadata. Period token columns and cache rates are scoped; timestamps/tool calls retain clear lifetime labels. `--period all` reconciles ledger totals with lifetime summaries. `FullDumpView` retains its raw session diagnostic purpose. Use coverage separately for unavailable-session metadata when there are no daily rows.

```jsx
// Add to HARNESS_TABLE in frontend/src/theme.js:
codex_cli: { label: "Codex", icon: "◇", color: () => "#60a5fa" },

// Render near usage totals when summary.attribution.legacy_tokens > 0:
<p className="text-xs text-subtext dark:text-subtext-dark">
  Some historical usage is assigned to session start dates.
</p>
```

Add conditional plain-language notices for partial and unavailable usage; do not describe an unavailable session as having consumed zero tokens. Ensure reasoning is identified as part of output, not a fifth additive slice.

- [x] **Step 4: Run tests and verify they pass; repeat Steps 1–4 for model switching counting one session; same ID across sources counts two; midnight/DST grouping; mixed legacy/measured data; custom ranges and rolling windows; project/source/model filters; unavailable sessions; cache efficiency with scoped counts; lifetime metadata labels.** Run `.venv/bin/python -m pytest tests/test_daily_reporting.py tests/test_store_report.py tests/test_dashboard_queries.py tests/test_dashboard_server.py -q`; expected: PASS. Run `npm run build` in `frontend`; follow the existing CI policy for bundled static assets rather than hand-editing minified files.
- [x] **Step 5: Commit runtime changes and passing tests together** with `feat: report tokens by actual usage day`.

### Task 6: Synchronize usage events independently and retry corrections

**Files:** Modify `src/stores/__init__.py`, `src/stores/supabase.py`, `src/commands/common.py`, `src/pipeline.py`; create `docs/migrations/2026-10-08-usage-events.sql`, `tests/test_usage_sync.py`; modify `tests/test_supabase_store.py`, `tests/test_sync_command.py`, `tests/test_pipeline_multi_store.py`.

**Interfaces:** Optional `UsageEventStore` protocol with `upsert_events(events: list[UsageEvent]) -> int`. `SupabaseStore(..., usage_table: str | None = None)` enables event writes explicitly. Existing `table` option and session conflict key remain unchanged. SQLite event acknowledgment interfaces are from Task 2.

- [x] **Step 1: Write the failing independent-retry test in `tests/test_usage_sync.py`.**

```python
from src.commands.common import run_sync
from src.models import SessionRecord
from src.stores.sqlite import SqliteStore
from src.usage import CollectionBatch, UsageCoverage
from tests.usage_helpers import event

def test_event_failure_retries_after_sessions_succeed(tmp_path):
    class Remote:
        name = 'remote'
        fail_events = True
        session_pushes = 0
        def upsert(self, records):
            self.session_pushes += len(records)
            return len(records)
        def upsert_events(self, events):
            if self.fail_events:
                raise RuntimeError('event table unavailable')
            return len(events)
        def close(self):
            pass
    store = SqliteStore(tmp_path / 'usage.db')
    rec = SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08',input_tokens=100)
    store.upsert_batch(CollectionBatch((rec,), (event(),),
        (UsageCoverage('codex_cli','s1','measured'),)))
    remote = Remote()
    run_sync(store,[remote],False)
    assert store.unsynced_for('remote') == []
    assert len(store.unsynced_events_for('remote')) == 1
    remote.fail_events = False
    run_sync(store,[remote],False)
    assert store.unsynced_events_for('remote') == []
    assert remote.session_pushes == 1
```

- [x] **Step 2: Run the test and verify the expected failure.**

Run: `.venv/bin/python -m pytest tests/test_usage_sync.py::test_event_failure_retries_after_sessions_succeed -v`
Expected: FAIL because event sync is never retried or acknowledged independently of session sync.
- [x] **Step 3: Add capability detection and independent sync paths.** Reuse `run_sync` for both pipeline remote pushes and the post-run pending sweep, keeping SQLite success mandatory and remote failure nonfatal. Acknowledge session and event batches separately only after each succeeds. Add `events_pushed`/`events_pending` fields to results; preserve existing `pushed`, `pending`, and `failed` fields. A legacy store receives sessions and a bounded warning; its unsupported events remain pending, never marked synchronized. Dry-run never creates the remote client or writes acknowledgments.

Implement Supabase event mapping using the dataclass fields, preserving stored event date/offset, with `on_conflict="source,session_id,event_id"`. Require explicitly configured `usage_table`; do not silently create or modify remote tables. Document an additive Postgres migration with all event fields, the conflict key, date/session indexes, and existing permission/RLS conventions. Coverage metadata must accompany synced session summaries for remote consumers to distinguish partial/unavailable data: add optional remote session columns and write them only when event capability is enabled. The implementation's event-aware remote batch path takes `CollectionBatch` internally while retaining the public session-only `upsert`.

- [x] **Step 4: Run tests and verify they pass; repeat Steps 1–4 for failed sessions with successful events, failed events with successful sessions, remote down during scheduled collect, independent store acknowledgments, corrected event resync, unchanged-event no-op, missing configured event table, session-only third-party store warning, dry-run counts, and optional dependency behavior.** Verify Supabase mocks assert the event conflict key and contain no raw cwd or conversation fields. Run `.venv/bin/python -m pytest tests/test_usage_sync.py tests/test_supabase_store.py tests/test_sync_command.py tests/test_pipeline_multi_store.py -q`; expected: PASS.
- [x] **Step 5: Commit runtime changes and passing tests together** with `feat: sync daily usage events with independent retries`.

### Task 7: Verify end-to-end integration test-first, then update documentation

**Files:** Create `tests/test_codex_daily_usage_e2e.py`; reuse `tests/usage_helpers.py` and source builders created in Tasks 1 and 3. Update tests owned by Tasks 1–6 only when an integration gap requires an additional regression. Finally modify `README.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, and `pyproject.toml`.

**Interfaces:** No new runtime interfaces. Consumes the collector, batch persistence, reporting, and retry APIs verified in Tasks 1–6; produces documented import, legacy attribution, timezone, and optional remote migration behavior.

- [x] **Step 1: Write the end-to-end integration regression before making integration fixes.** Use synthetic source fixtures and temporary databases. Execute `CollectCommand` with monkeypatched home/config and a temporary SQLite path. Two usage responses on different local days must yield one session, two events, and matching all-time tokens. Append a third response to the old session, collect with a one-day activity lookback, move the file to archive, and collect again. Assert three events, unchanged earlier dates, no duplicate totals, normalized names, and masked project identity. Invoke report and dashboard query paths against that same temporary database; simulate event sync failure followed by successful retry using the Task 6 fake remote.

Start with this command-to-database regression, then extend it with the report and sync assertions described above before making any integration corrections:

```python
import json
import sqlite3
from pathlib import Path
import tracker
from src.config import Config, Paths
from src.dashboard import queries


def test_collect_append_archive_preserves_daily_totals(tmp_path, monkeypatch):
    cfg = Config(paths=Paths(copilot_home=tmp_path/'copilot',
        claude_projects=tmp_path/'claude', codex_home=tmp_path/'codex'),
        db_path=tmp_path/'usage.db', track_project_names='no', context='work')
    monkeypatch.setattr(Config, 'load', classmethod(lambda cls, **kw: cfg))
    monkeypatch.setenv('CODEX_HOME', str(cfg.paths.codex_home))
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    # Noon UTC stays on the same local date in this test, independent of the machine zone.
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-09-01T12:00:00Z', cwd=str(tmp_path/'project'), source='vscode')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex'))]
    def response(rid, day, tokens):
        return dict(type='token_usage_record', timestamp=f'{day}T12:00:00Z',
            payload=dict(session_id='s1', thread_id='s1', turn_id='t1',
                response_id=rid, usage=dict(input_tokens=tokens, output_tokens=0)))
    rows += [response('r1','2026-10-08',100), response('r2','2026-10-09',50)]
    path = cfg.paths.codex_home/'sessions'/'rollout.jsonl'
    path.parent.mkdir(parents=True)
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
    parser = tracker.build_parser()
    def collect():
        args = parser.parse_args(['--db',str(cfg.db_path),'collect','--lookback','1'])
        assert args.run(args) == 0
    collect()
    with sqlite3.connect(cfg.db_path) as conn:
        original = conn.execute('SELECT event_id,date,utc_offset_minutes FROM usage_events ORDER BY event_id').fetchall()
        assert len(original) == 2
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(response('r3','2026-10-10',25))+'\n')
    collect()
    archived = cfg.paths.codex_home/'archived_sessions'/'renamed.jsonl'
    archived.parent.mkdir(parents=True)
    path.rename(archived)
    collect()
    with sqlite3.connect(cfg.db_path) as conn:
        conn.row_factory = sqlite3.Row
        assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM usage_events').fetchone()[0] == 3
        current = conn.execute('SELECT event_id,date,utc_offset_minutes FROM usage_events ORDER BY event_id').fetchall()
        assert [tuple(row) for row in current[:2]] == original
        summary = queries.summary(conn,'all')
        assert (summary['total_tokens'],summary['session_count']) == (175,1)
        record = conn.execute('SELECT * FROM sessions').fetchone()
        assert record['input_tokens'] == 175
        assert record['context'] == 'work'
        assert record['canonical_model'] == 'gpt-5.3-codex'
        assert record['project'] and record['project'] != str(tmp_path/'project')
    report_args = parser.parse_args(['--db',str(cfg.db_path),'report','--period','all','--summary','--json'])
    assert report_args.run(report_args) == 0
```

The freshly written/appended file's mtime selects this older session with the normal one-day lookback. For precise midnight/DST attribution, use the explicitly injected timezone tests in Tasks 1–3 instead of relying on this test machine's timezone.

- [x] **Step 2: Run the integration regression and inspect the result.**

Run: `.venv/bin/python -m pytest tests/test_codex_daily_usage_e2e.py -v`
Expected: a behavioral FAIL if an integration requirement is missing. If it already passes because Tasks 1–6 deliver the complete flow, keep the passing regression; do not manufacture a failure. For each genuine integration defect, reproduce it with a failing assertion before editing runtime code.

- [x] **Step 3: Apply the smallest integration correction and verify the tests pass.** Run the integration test after each correction, then the focused suites below; expected: PASS. Audit the matrix against named tests already added in Tasks 1–6. For any uncovered requirement, add its failing regression in the owning test file first and repeat the test-first sequence. Commit integration corrections and their passing tests together before changing documentation.

#### Required Codex scenario matrix

Every row is required before completion. Tasks 1–6 implement their rows test-first in the owning task; Task 7 audits coverage and adds the end-to-end flow. This matrix is not a deferred test-writing phase. This covers supported source variants and defined failure behavior; it does not claim support for unknown future Codex schemas. Use explicit fixtures for both a current per-response rollout and an older cumulative-snapshot rollout. Keep fixture files synthetic and share builders rather than copying real transcripts.

| Scenario | Required result | Owning test file |
|---|---|---|
| CLI and editor source metadata | Both persisted variants collected and displayed as Codex | `test_codex_cli_collector.py` |
| Default home, `CODEX_HOME`, explicitly injected path | Correct directory precedence and path expansion | `test_config.py` |
| Missing home, absent active/archive directory, empty file | No crash; no invented events | `test_codex_cli_collector.py` |
| Unreadable file and disappearing file during scan | Bounded diagnostic; other sessions still collected | `test_codex_cli_collector.py` |
| Nested active and archived rollouts | Both locations discovered; same session not duplicated | `test_codex_cli_collector.py` |
| Rollout renamed or moved into archive | Metadata ID and event identity remain stable | `test_codex_cli_collector.py` |
| Metadata ID different from filename | Metadata ID wins | `test_codex_cli_collector.py` |
| Missing/invalid session metadata or missing timestamp | Unsupported entry diagnosed; no fake session ID or date | `test_codex_cli_collector.py` |
| Current per-response usage | Accepted response counts and sums equal fixture values | `test_codex_cli_collector.py` |
| Per-response and cumulative entries coexist | Only per-response accounting contributes | `test_codex_cli_collector.py` |
| Duplicate response entries and duplicate token notifications | One contribution per unique response/delta | `test_codex_cli_collector.py` |
| Response ID missing | Stable fingerprint; partial coverage visible | `test_codex_cli_collector.py` |
| Old cumulative-only rollout with known zero baseline | Correct deltas; no repeated cumulative sum | `test_codex_cli_collector.py` |
| Old snapshot with null/missing info | Skipped without creating a zero response | `test_codex_cli_collector.py` |
| Nonzero initial snapshot with inherited/unknown baseline | No invented first delta; partial coverage | `test_codex_cli_collector.py` |
| Snapshot counter decrease/reset | Previous usage retained; ambiguous reset warned; explicit fresh boundary handled | `test_codex_cli_collector.py` |
| Only last-request usage with no cumulative baseline or response ID | Unsupported attribution visible; no guessed daily totals | `test_codex_cli_collector.py` |
| One session across two days and several idle days | Tokens on response days only; one lifetime session | `test_codex_daily_usage_e2e.py` |
| Session created before lookback but recently active | Scheduled collection updates complete selected history | `test_codex_daily_usage_e2e.py` |
| Session untouched before lookback | Not imported by the short window; imported by explicit backfill | `test_codex_cli_collector.py` |
| Append usage after collection; recollect twice | Only new event added; earlier totals unchanged | `test_codex_daily_usage_e2e.py` |
| Context clear or compaction preserving session ID | Prior consumption retained; subsequent events stay in session | `test_codex_cli_collector.py` |
| Context clear producing a new session ID | Separate session; no overwriting old usage | `test_codex_cli_collector.py` |
| Rollback, aborted turn, or failed task after recorded usage | Consumed tokens retained despite conversation/task state | `test_codex_cli_collector.py` |
| Root/child response ownership with separate counters | Each response counted once under originating session | `test_codex_cli_collector.py` |
| Parent counters including descendants | No child/root double count; uncertain variants marked partial | `test_codex_cli_collector.py` |
| Fork copying parent history | Inherited responses excluded from the fork's new consumption | `test_codex_cli_collector.py` |
| Fork or descendant ownership missing/ambiguous | Partial coverage and diagnostic; no guessed ownership | `test_codex_cli_collector.py` |
| Model changes within session | Separate raw-model totals; one distinct session | `test_codex_cli_collector.py`, `test_daily_reporting.py` |
| Missing model and usage preceding turn context | Preserve unknown when attribution cannot be established | `test_codex_cli_collector.py` |
| Known name, dated name, configured alias, unknown name | Existing normalization semantics; raw identity retained | `test_model_normalize.py`, `test_middleware_model_normalize.py` |
| All usage categories, zero cache, missing optional category | Correct non-overlapping totals and subset semantics | `test_usage.py` |
| Negative, boolean, fractional, string, null, or excessive subset counts | Rejected with diagnostic; unrelated entries survive | `test_usage.py`, `test_codex_cli_collector.py` |
| Explicit recorded zero usage versus no usage records | Zero measurement distinguishable from unavailable coverage | `test_codex_cli_collector.py` |
| Invalid JSON in middle, blank lines, Unicode, non-object JSON | File continues safely with visible partial status when appropriate | `test_codex_cli_collector.py` |
| Partial final line completed on next import | Earlier events retained; completed event then imported once | `test_codex_cli_collector.py` |
| UTC midnight differs from local midnight | Correct stored local response day | `test_usage.py`, `test_daily_reporting.py` |
| DST spring jump and fall repeated hour | Correct historical offset/date; distinct responses retained | `test_usage.py` |
| Collector machine timezone changes between imports | Existing persisted local dates/offsets remain stable | `test_sqlite_usage.py` |
| Large streaming file and truncated available history | Bounded parser memory; partial history identified; no fabricated baseline | `test_codex_cli_collector.py` |
| Tool calls in function/custom formats with duplicated call IDs | Deduplicated lifetime count and correct request footprint | `test_codex_cli_collector.py` |
| Project modes yes/no/whimsical and work/personal context | Existing identity behavior; no cwd or transcript fields persisted/synced | `test_project_resolver.py`, `test_context.py`, `test_codex_daily_usage_e2e.py` |
| Existing database and repeated additive migration | Session rows and prior acknowledgments preserved | `test_sqlite_usage.py` |
| Invalid event during batch write | Session, event, and coverage writes roll back together | `test_sqlite_usage.py` |
| Corrected event versus unchanged reimport | Corrected values resync; unchanged values retain acknowledgments | `test_sqlite_usage.py`, `test_usage_sync.py` |
| Mixed Claude/Copilot legacy and Codex measured/partial/unavailable | No double counting or fabricated residual usage; disclosures match | `test_daily_reporting.py` |
| Day/month/year/all and custom dashboard ranges | Scoped tokens reconcile with ledger; all-time totals match lifetime | `test_daily_reporting.py`, `test_store_report.py` |
| Rolling windows, trends, heatmaps, source/model/project filters | Same daily attribution across all report surfaces | `test_dashboard_queries.py`, `test_daily_reporting.py` |
| Same session ID across sources; multiple models/days | Distinct source/session counts without row inflation | `test_daily_reporting.py` |
| Existing third-party collector/store without batch/event support | Session-only compatibility plus explicit unsupported-sync notice | `test_pipeline.py`, `test_usage_sync.py` |
| Session sync success/event failure and reverse | Independent acknowledgments; failed unit retries | `test_usage_sync.py` |
| Two remote stores with independent failures | Per-store retry state retained; SQLite collection succeeds | `test_pipeline_multi_store.py` |
| Dry-run, missing remote event table, optional Supabase dependency | No unintended writes; actionable failure; existing session sync works | `test_usage_sync.py`, `test_supabase_store.py` |
| End-to-end scheduled lookback, archive move, report, sync retry | No lost/duplicated usage through the complete flow | `test_codex_daily_usage_e2e.py` |

Run the focused suites created throughout Tasks 1–6 and the integration suite:

```bash
.venv/bin/python -m pytest tests/test_usage.py tests/test_sqlite_usage.py tests/test_codex_cli_collector.py tests/test_daily_reporting.py tests/test_usage_sync.py tests/test_codex_daily_usage_e2e.py -q
```

Add parameterized invalid-count and timestamp cases rather than one repeated test per scalar. Tests must assert results and user-visible diagnostics, not merely that the collector did not raise. Marking a supported scenario skipped is not completion. If a scenario requires an unsupported schema, assert the documented partial/unavailable behavior instead.
- [x] **Step 4: After the complete Codex suite passes, update `CLAUDE.md`, `README.md`, architecture documentation, and package metadata to match the final implementation.** Add Codex to supported sources and package keywords/description. Explain `CODEX_HOME`, active/archive discovery, measured daily attribution, response-count semantics, partial/unavailable usage, and unchanged historical Claude/Copilot start-date allocation. Replace the stale blanket claim that editor sessions never persist data with the verified Codex persisted-log support. Explain that context clearing preserves consumption and that session identity follows the source ID. Document aliases as optional, distinct model variants preserved, and user alias-file precedence.

Include these usage examples, clearly separating local collection from optional remote preparation:

```bash
tokentracer collect --lookback 30
tokentracer report --period all --summary --json
tokentracer sync --dry-run
```

```toml
[stores.supabase]
url = "${SUPABASE_URL}"
key = "${SUPABASE_KEY}"
table = "token_sessions"
usage_table = "token_usage_events"
```

Explain that lookback selects recently active files and imports their complete available histories. Remote operators must apply the checked-in migration before enabling `usage_table`. Document compatibility behavior for stores without event capability. Do not run the examples against the user's live data or apply remote migration as a test.

- [x] **Step 5: Run `.venv/bin/python -m pytest -q` from the repository root and `npm run build` in `frontend`.** Rehearse additive migration using a temporary copy of a synthetic pre-feature database. Verify existing rows and acknowledgments survive, ledger reimports are stable, and tests use temporary paths. Review the SQL and payloads for privacy exclusions.
- [x] **Step 6: Commit documentation and package metadata** with `docs: document Codex daily usage and verify migration`. Runtime corrections belong in the earlier commit with their regression tests.

## Self-review and execution handoff

- [x] Verify every implementation task records a failing-test run before runtime edits, a passing focused run, and a commit containing both code and tests.
- [x] Verify all eight acceptance criteria in the spec map to tests above.
- [x] Verify the optional collector/store method signatures are consistent across tasks and session-only tests still pass.
- [x] Verify no session contributes both ledger and legacy tokens, and all period queries use the same attribution source.
- [x] Verify timezone reassignment, malformed tails, resumed sessions, fork ownership, and event sync retry each have a regression test.
- [x] Review and settle fork/subagent fixture evidence before enabling those variants; unsupported ownership remains visibly partial.
- [x] Have the user review this concrete plan and select an execution method before implementation, as required by the writing-plans skill.

Recommended execution: **Native**, because the seven tasks share accounting, identity, persistence, and sync interfaces and benefit from one continuous implementation context. A final independent review should concentrate on double counting, migrations, timezone boundaries, and remote retry semantics.


## Execution record

Implemented natively on `codex-support` after approval. Baseline reporting fixtures
were corrected first (`609ebf3`); Tasks 1–6 and integration corrections each have
separate code/test commits. The integration checks also pin persisted response
precedence, exclusion of ambiguous parent snapshots while retaining raw audit
history, coverage persistence across lookback windows, and stale-event
acknowledgment protection. Those conservative ownership decisions supersede
naively summing every raw ledger row. Remote consumers must follow the documented
attribution rules. Runtime code and integration tests were committed before the
final documentation update.

Verification before final independent review: 451 Python tests passed, three
frontend rendering tests passed, and the production frontend build passed into
`/private/tmp/tokentracer-frontend-build`. CI-owned committed static assets were
preserved. The checked-in remote SQL migration was reviewed but not applied to
live infrastructure.
