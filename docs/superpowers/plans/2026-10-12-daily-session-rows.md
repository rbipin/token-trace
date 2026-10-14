# Daily Session Rows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store token usage as one `sessions` row per `(session_id, source, model, date)` and remove the separate usage-event ledger.

**Architecture:** Collectors split each session into per-local-day `SessionRecord`s. `SqliteStore.upsert` replaces all rows of each collected `(session_id, source)` in one transaction. Reports and the dashboard read `sessions` directly and aggregate day rows when they need a session view. Supabase mirrors the replace with delete-then-upsert on a widened conflict key.

**Tech Stack:** Python 3.11+ standard library, SQLite, pytest, optional `supabase>=2.0`, React/Vite frontend (node test runner).

**Spec:** `docs/superpowers/specs/2026-10-12-daily-session-rows-design.md`

## Global Constraints

- Python 3.11+; standard library only at runtime except the existing optional Supabase dependency.
- Session primary key: `(session_id, source, model, date)`; `sync_log` key: `(session_id, source, model, date, store_name)`; Supabase conflict key: `"session_id,source,model,date"`.
- `date` is the local calendar day of the activity; when a source only has a session total, use the session's start date.
- All non-key columns on a row describe that day only. Session views aggregate: `SUM` counts, `MIN(start_ts)`, `MAX(end_ts)`, `MAX(context_peak_tokens)`.
- Re-collect replaces all rows of each collected `(session_id, source)` in one transaction.
- `SessionRecord` stays a frozen dataclass; transform with `dataclasses.replace()`.
- Collectors are read-only with respect to their source files.
- Tests use synthetic fixtures and temporary databases only. Never collect live user data or apply a remote migration in a test.
- Do not rebuild the committed frontend bundle; validate builds with `npm run build -- --outDir /private/tmp/tokentracer-frontend-build`.
- Commit messages follow Conventional Commits; no agent co-author trailer.

## Review Focus

1. **Old database with orphan `sync_log` rows** (sync entry whose session row is gone): migration must drop them, not crash. Test in Task 4.
2. **Very old database whose `sessions` table lacks `context` / `canonical_model`**: the additive column checks must run before the key rebuild. Test in Task 4.
3. **Claude transcripts that mix timed and untimed assistant messages**: untimed usage goes to the session's start day and is not lost. Test in Task 5.
4. **Large Supabase backfill** (hundreds of sessions in one push): the remote delete must be chunked so the request URL stays bounded. Test in Task 8.
5. **Partially synced sessions after migration** (one model synced, another not): `unsynced_for` must return every row of the session, because the remote replace deletes all of its rows. Test in Task 4.
6. **Copilot `created_at` values in both SQLite (`YYYY-MM-DD HH:MM:SS`, naive UTC) and ISO `...Z` form**: both must map to the right local day. Test in Task 7.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/models.py` | modify | `SessionRecord.key` and `merge_records` include `date` |
| `src/stores/sqlite.py` | restore from `main`, then modify | daily key schema, migration, replace-per-session upsert, sync log |
| `src/stores/sqlite_usage.py` | delete | retired ledger |
| `src/usage.py` | delete (contents move into `codex_cli.py`) | — |
| `src/stores/supabase.py` | restore from `main`, then modify | delete-then-upsert, new conflict key |
| `src/stores/__init__.py`, `src/pipeline.py`, `src/commands/common.py`, `src/commands/sync.py`, `src/middleware/model_normalize.py`, `src/collectors/base.py` | restore from `main` | session-only flow |
| `src/collectors/__init__.py`, `src/commands/collect.py` | modify | keep Codex wiring, drop event plumbing |
| `src/collectors/claude_cli.py` | modify | per-day records |
| `src/collectors/codex_cli.py` | modify | per-day records from deduplicated events; owns event helpers |
| `src/collectors/copilot_cli.py` | modify | per-day records from `assistant_usage_events` |
| `src/report.py`, `src/dashboard/queries.py` | modify | read `sessions`; no attribution |
| `frontend/src/components/UsageAttribution.jsx` | delete | — |
| `frontend/src/pages/TokensPage.jsx`, `frontend/tests/usage.test.mjs` | modify | drop attribution UI/test |
| `docs/migrations/2026-10-08-usage-events.sql` | delete | never applied |
| `docs/migrations/2026-10-12-daily-session-rows.sql` | create | remote key change, applied manually by the user |
| Docs (`CLAUDE.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN-HISTORY.md`, `changelog.md`) | modify | document verified behavior |

---

### Task 1: Back up the local database

No code. Do this before any task runs `tracker.py` against the real database. Tests never touch it.

**Files:** none in the repo.

- [ ] **Step 1: Find the database the user actually uses**

Run: `ls -l ~/.tokentracer/usage.db /Users/bipin/repo/TokenTracer/usage.db 2>/dev/null`
Expected: one or both paths listed. Show the result to the user and ask which to back up (both if both exist). Do not continue without the answer.

- [ ] **Step 2: Take a consistent copy with SQLite's backup command**

Run (for each confirmed path `<db>`): `sqlite3 "<db>" ".backup '<db>.bak-2026-10-12'"`
Expected: no output.

- [ ] **Step 3: Verify the copy**

Run: `sqlite3 "<db>.bak-2026-10-12" "PRAGMA integrity_check; SELECT COUNT(*) FROM sessions;"`
Expected: `ok` and the same row count as `sqlite3 "<db>" "SELECT COUNT(*) FROM sessions;"`. Report both counts to the user.

---

### Task 2: Reports and dashboard read `sessions` directly

Removes the dependency on the `reporting_usage` view and the attribution disclosure, while the ledger still exists. After this task nothing reads ledger objects.

**Files:**
- Modify: `src/report.py`
- Modify: `src/dashboard/queries.py`
- Delete: `frontend/src/components/UsageAttribution.jsx`
- Modify: `frontend/src/pages/TokensPage.jsx:10,96`
- Modify: `frontend/tests/usage.test.mjs`
- Replace: `tests/test_daily_reporting.py`

**Interfaces:**
- Consumes: `SqliteStore.upsert(records) -> int` (existing).
- Produces: `queries.summary(...)` without an `"attribution"` key; `UsageReporter.report(...)` JSON without `"attribution"` / `"activity_scope"`; a temp view `period_sessions` grouped by `(source, session_id, model)` that Task 4 relies on.

- [ ] **Step 1: Replace `tests/test_daily_reporting.py` with failing tests**

```python
import json
import sqlite3

from src.dashboard import queries
from src.models import SessionRecord
from src.report import UsageReporter
from src.stores.sqlite import SqliteStore


def _rec(sid, day, model='gpt-5.3-codex', source='codex_cli', **kw):
    return SessionRecord(sid, source, model=model, date=day, **kw)


def _summary(path, *args):
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return queries.summary(conn, *args)


def test_dashboard_scopes_tokens_by_row_date(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', input_tokens=100),
                              _rec('s2', '2026-10-09', input_tokens=50)])
    assert _summary(path, 'custom', '2026-10-08', '2026-10-08')['total_tokens'] == 100
    assert _summary(path, 'all')['total_tokens'] == 150


def test_session_count_is_distinct_source_and_session(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', model='a'),
                              _rec('s1', '2026-10-08', model='b'),
                              _rec('s1', '2026-10-08', source='claude_cli')])
    assert _summary(path, 'all')['session_count'] == 2


def test_summary_has_no_attribution_block(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', input_tokens=1)])
    assert 'attribution' not in _summary(path, 'all')


def test_cli_report_has_no_lifetime_labels_or_notices(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', input_tokens=1)])
    text = UsageReporter(path).report(period='all')
    assert 'Lifetime' not in text
    assert 'session start dates' not in text
    payload = json.loads(UsageReporter(path).report(period='all', as_json=True))
    assert 'attribution' not in payload
    assert 'activity_scope' not in payload['rows'][0]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python3 -m pytest tests/test_daily_reporting.py -q`
Expected: `test_summary_has_no_attribution_block` and `test_cli_report_has_no_lifetime_labels_or_notices` FAIL (`attribution` present / `Lifetime` in text).

- [ ] **Step 3: Update `src/dashboard/queries.py`**

1. Replace every `FROM reporting_usage` with `FROM sessions` (in `_rolling_stats`, `summary` x3, `heatmap`, `trend`, `projects`).
2. In `summary`, change the `session_count` entry to read `sessions` and delete the `"attribution"` entry:

```python
        "session_count": conn.execute(
            f"SELECT COUNT(*) FROM (SELECT source, session_id FROM sessions "
            f"WHERE {where}{extra} GROUP BY source, session_id)", params,
        ).fetchone()[0],
```

3. Delete the whole `attribution()` function.

- [ ] **Step 4: Update `src/report.py`**

1. Delete `from .dashboard.queries import attribution`.
2. In `SessionsDetailedView` and `SessionsListView` SQL, delete the line `'lifetime' AS activity_scope,`.
3. Restore the `main` header labels:
   - `SessionsDetailedView`: `headers=["Project", "Source", "Model", "Start", "End", "Input", "Output", "Reasoning", "CacheRead", "CacheCreate", "CacheHit%", "CtxPeak", "Turns", "Tools"]`
   - `PeriodSummaryView`: `headers=["Period", "Source", "Model", "Turns", "Input", "Output", "CacheCreate", "CacheRead"]`
   - `ByProjectView`: `headers=["Project", "Date", "Model", "Turns", "Input", "Output", "CacheRead"]`
   - `SessionsListView`: `headers=["Session", "Project", "Date", "Start", "End", "Turns", "Tokens", "CacheHit%"]`
4. In `PeriodSummaryView`, `ByProjectView`, and `_cache_efficiency`, replace `FROM reporting_usage` with `FROM sessions`.
5. Replace the body of `report()` inside `try:` with:

```python
            ctx = self._make_context(conn, 'all' if detailed else period, models, as_json)
            conn.execute(
                f"CREATE TEMP TABLE scoped_usage AS SELECT * FROM sessions "
                f"WHERE {ctx.date_filter}{ctx.model_filter}", ctx.params)
            # One row per session/model inside the period: day rows are summed,
            # timestamps span the period's first and last activity.
            conn.execute("""CREATE TEMP VIEW period_sessions AS
                SELECT session_id, source, model, canonical_model, MIN(date) AS date, project,
                    MIN(start_ts) AS start_ts, MAX(end_ts) AS end_ts,
                    SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens,
                    SUM(cache_read_tokens) AS cache_read_tokens,
                    SUM(cache_creation_tokens) AS cache_creation_tokens,
                    SUM(reasoning_tokens) AS reasoning_tokens,
                    MAX(context_peak_tokens) AS context_peak_tokens,
                    SUM(turns) AS turns, SUM(tool_calls) AS tool_calls
                FROM scoped_usage GROUP BY source, session_id, model
            """)
            return _pick_strategy(summary, by_project, period, detailed).render(ctx)
```

- [ ] **Step 5: Remove the attribution UI**

1. `git rm frontend/src/components/UsageAttribution.jsx`
2. In `frontend/src/pages/TokensPage.jsx` delete line 10 `import UsageAttribution from "../components/UsageAttribution.jsx";` and line 96 `<UsageAttribution attribution={summary?.attribution} />`.
3. In `frontend/tests/usage.test.mjs` delete the test `'partial and unavailable usage is disclosed without inventing zero consumption'`.

- [ ] **Step 6: Run focused tests and verify they pass**

Run: `python3 -m pytest tests/test_daily_reporting.py tests/test_store_report.py tests/test_dashboard_queries.py tests/test_dashboard_server.py -q`
Expected: PASS. If a test still asserts `Lifetime*` / `Requests` labels or an `attribution` key, update it to the `main` labels above.

Run: `cd frontend && node --test tests/usage.test.mjs`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A src/report.py src/dashboard/queries.py frontend tests/test_daily_reporting.py tests/test_store_report.py tests/test_dashboard_queries.py
git commit -m "refactor: report usage from sessions table"
```

---

### Task 3: Remove the usage-event ledger

The pipeline, stores, and sync return to the session-only flow from `main`. Codex still yields lifetime summaries through `collect()` until Task 6.

**Files:**
- Restore from `main`: `src/pipeline.py`, `src/stores/__init__.py`, `src/stores/sqlite.py`, `src/stores/supabase.py`, `src/commands/common.py`, `src/commands/sync.py`, `src/middleware/model_normalize.py`, `src/collectors/base.py`, `tests/test_pipeline.py`, `tests/test_middleware_model_normalize.py`, `tests/test_supabase_store.py`, `tests/test_sync_command.py`, `tests/test_sync_excludes_identities.py`
- Delete: `src/stores/sqlite_usage.py`, `tests/test_sqlite_usage.py`, `tests/test_usage_sync.py`, `tests/test_codex_daily_usage_e2e.py`, `tests/usage_helpers.py`, `docs/migrations/2026-10-08-usage-events.sql`
- Modify: `src/stores/sqlite.py` (after restore), `src/collectors/__init__.py`, `src/commands/collect.py`, `src/collectors/codex_cli.py`
- Create: `tests/test_ledger_removal.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `TrackerPipeline.run()` calls only `collector.collect(since)`; `RunResult` without `events_written`; `run_sync(sqlite_store, remote_stores, dry_run) -> dict` returning `{"pending": N}` or `{"pushed": N, "failed": bool[, "error": str]}`; `SqliteStore` exposes only `upsert`, `close`, `unsynced_for(store_name)`, `mark_synced(records, store_name)`, `record_run(timestamp=None)`.

- [ ] **Step 1: Write the failing test `tests/test_ledger_removal.py`**

```python
import sqlite3
from datetime import date

from src.models import SessionRecord
from src.pipeline import TrackerPipeline
from src.stores.sqlite import SqliteStore

LEDGER = {'usage_events', 'usage_coverage', 'usage_event_sync_log',
          'usage_coverage_sync_log', 'usage_daily', 'reporting_usage'}


def test_store_drops_event_ledger_objects(tmp_path):
    path = tmp_path / 'usage.db'
    with sqlite3.connect(path) as conn:
        for table in ('usage_events', 'usage_coverage', 'usage_event_sync_log', 'usage_coverage_sync_log'):
            conn.execute(f'CREATE TABLE {table} (x)')
        conn.execute('CREATE VIEW usage_daily AS SELECT x FROM usage_events')
        conn.execute('CREATE VIEW reporting_usage AS SELECT x FROM usage_daily')
    SqliteStore(path)
    with sqlite3.connect(path) as conn:
        names = {r[0] for r in conn.execute('SELECT name FROM sqlite_master')}
    assert not names & LEDGER


def test_pipeline_uses_collect_only(tmp_path):
    class Both:
        source = 'codex_cli'

        def collect(self, since):
            return [SessionRecord('s1', 'codex_cli', date='2026-10-08', input_tokens=5)]

        def collect_batch(self, since):
            raise AssertionError('ledger path removed')

    result = (TrackerPipeline().add(Both()).since(date(2026, 10, 1))
              .stores(SqliteStore(tmp_path / 'usage.db')).run())
    assert result.records_written == 1
    assert result.errors == []
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python3 -m pytest tests/test_ledger_removal.py -q`
Expected: both FAIL (ledger tables still present; pipeline calls `collect_batch`).

- [ ] **Step 3: Restore session-only files from `main`**

```bash
git checkout main -- src/pipeline.py src/stores/__init__.py src/stores/sqlite.py src/stores/supabase.py \
  src/commands/common.py src/commands/sync.py src/middleware/model_normalize.py src/collectors/base.py \
  tests/test_pipeline.py tests/test_middleware_model_normalize.py tests/test_supabase_store.py \
  tests/test_sync_command.py tests/test_sync_excludes_identities.py
git rm src/stores/sqlite_usage.py tests/test_sqlite_usage.py tests/test_usage_sync.py \
  tests/test_codex_daily_usage_e2e.py tests/usage_helpers.py docs/migrations/2026-10-08-usage-events.sql
```

- [ ] **Step 4: Drop ledger objects in `SqliteStore._migrate`**

In `src/stores/sqlite.py`, inside `_migrate`, insert immediately before the final `conn.commit()`:

```python
            # Remove the retired per-event usage ledger (superseded by daily session rows)
            conn.execute("DROP VIEW IF EXISTS reporting_usage")
            conn.execute("DROP VIEW IF EXISTS usage_daily")
            for table in ("usage_events", "usage_coverage",
                          "usage_event_sync_log", "usage_coverage_sync_log"):
                conn.execute(f"DROP TABLE IF EXISTS {table}")
```

- [ ] **Step 5: Drop event plumbing from collector exports and the collect command**

`src/collectors/__init__.py`:

```python
"""Collectors package."""

from .base import ActivityCollector
from .codex_cli import CodexCliCollector
from .claude_cli import ClaudeCliCollector
from .copilot_cli import CopilotCliCollector

__all__ = [
    "ActivityCollector",
    "CodexCliCollector",
    "ClaudeCliCollector",
    "CopilotCliCollector",
]
```

`src/commands/collect.py`: delete the two lines

```python
                if info.get("events_pushed"):
                    print(f"Synced {info['events_pushed']} pending usage event(s) to {store_name}")
```

and the line `f"and {getattr(result, 'events_written', 0)} usage events "`.

- [ ] **Step 6: Keep Codex diagnostics visible**

`src/collectors/codex_cli.py`: add `import sys` to the imports, and replace `collect()` with:

```python
    def collect(self, since: date) -> Iterator[SessionRecord]:
        batch = self.collect_batch(since)
        for message in batch.diagnostics:
            print(f"Warning: {message}", file=sys.stderr)
        yield from batch.sessions
```

- [ ] **Step 7: Run focused tests, then the full suite**

Run: `python3 -m pytest tests/test_ledger_removal.py -q`
Expected: PASS.

Run: `grep -rn "usage_helpers\|sqlite_usage\|upsert_batch\|unsynced_events_for\|mark_session_batch_synced" src tests`
Expected: no output.

Run: `python3 -m pytest -q`
Expected: PASS. `tests/test_codex_cli_collector.py` still passes because `collect_batch` exists until Task 6; if a test there writes through `store.upsert_batch` (`test_later_descendant_discovery_retains_raw_history_but_excludes_ambiguous_totals`, `test_late_child_excludes_persisted_parent_outside_lookback`), delete it — it tests persisted-ledger behavior the spec retires.

- [ ] **Step 8: Commit**

```bash
git add -A src tests docs/migrations
git commit -m "refactor!: remove usage event ledger" -m "BREAKING CHANGE: usage_events, usage_coverage and the reporting_usage view are dropped on first run."
```

---

### Task 4: Daily primary key, migration, and replace-per-session upsert

**Files:**
- Modify: `src/models.py`
- Modify: `src/stores/sqlite.py`
- Modify: `src/report.py` (`FullDumpView` sync subquery)
- Modify: `tests/test_models.py:12-14`
- Create: `tests/test_sqlite_daily_rows.py`
- Modify: `tests/test_daily_reporting.py` (append)

**Interfaces:**
- Consumes: `period_sessions` temp view from Task 2.
- Produces: `SessionRecord.key -> tuple[str, str, str, str]` = `(session_id, source, model, date)`; `merge_records` dedups on that key; `SqliteStore.upsert` replaces whole sessions; module constants `_SESSION_COLUMNS: tuple[str, ...]`, `_INSERT: str`; `sync_log` has a `date` column.

- [ ] **Step 1: Write failing tests `tests/test_sqlite_daily_rows.py`**

```python
import sqlite3
from dataclasses import replace

from src.models import SessionRecord, merge_records
from src.stores.sqlite import SqliteStore

OLD_SESSIONS = """CREATE TABLE sessions (
    session_id TEXT NOT NULL, source TEXT NOT NULL, model TEXT NOT NULL,
    date TEXT NOT NULL, start_ts TEXT, end_ts TEXT, project TEXT,
    turns INTEGER DEFAULT 0, tool_calls INTEGER DEFAULT 0, input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0, cache_creation_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0, context_peak_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    PRIMARY KEY (session_id, source, model))"""
OLD_SYNC_LOG = """CREATE TABLE sync_log (
    session_id TEXT NOT NULL, source TEXT NOT NULL, model TEXT NOT NULL,
    store_name TEXT NOT NULL, synced_at TEXT NOT NULL,
    PRIMARY KEY (session_id, source, model, store_name))"""


def _rec(day, sid='s1', **kw):
    return SessionRecord(sid, 'claude_cli', model='m', date=day, **kw)


def _rows(path):
    with sqlite3.connect(path) as conn:
        return conn.execute(
            'SELECT session_id, date, input_tokens FROM sessions ORDER BY session_id, date').fetchall()


def test_record_key_includes_date():
    assert _rec('2026-10-08').key == ('s1', 'claude_cli', 'm', '2026-10-08')
    assert len(merge_records([_rec('2026-10-08'), _rec('2026-10-09')])) == 2


def test_one_session_stores_one_row_per_day(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('2026-10-08', input_tokens=100), _rec('2026-10-09', input_tokens=50)])
    assert _rows(path) == [('s1', '2026-10-08', 100), ('s1', '2026-10-09', 50)]


def test_recollect_replaces_stale_days_of_that_session_only(tmp_path):
    path = tmp_path / 'usage.db'
    store = SqliteStore(path)
    store.upsert([_rec('2026-10-08', input_tokens=100), _rec('2026-10-09', input_tokens=50),
                  _rec('2026-10-01', sid='s2', input_tokens=7)])
    store.upsert([_rec('2026-10-10', input_tokens=150)])
    assert _rows(path) == [('s1', '2026-10-10', 150), ('s2', '2026-10-01', 7)]


def test_changed_session_is_fully_unsynced_and_unchanged_session_stays_synced(tmp_path):
    store = SqliteStore(tmp_path / 'usage.db')
    s1 = [_rec('2026-10-08', input_tokens=100), _rec('2026-10-09', input_tokens=50)]
    s2 = [_rec('2026-10-01', sid='s2', input_tokens=7)]
    store.upsert(s1 + s2)
    store.mark_synced(s1 + s2, 'supabase')
    store.upsert([s1[0], replace(s1[1], input_tokens=60)] + s2)
    assert sorted((r.session_id, r.date) for r in store.unsynced_for('supabase')) == [
        ('s1', '2026-10-08'), ('s1', '2026-10-09')]


def test_unsynced_for_returns_whole_session_when_any_row_is_unsynced(tmp_path):
    store = SqliteStore(tmp_path / 'usage.db')
    a, b = _rec('2026-10-08'), replace(_rec('2026-10-08'), model='m2')
    store.upsert([a, b, _rec('2026-10-01', sid='s2')])
    store.mark_synced([a, _rec('2026-10-01', sid='s2')], 'supabase')
    assert sorted(r.model for r in store.unsynced_for('supabase')) == ['m', 'm2']


def test_migration_rekeys_old_tables_and_preserves_data(tmp_path):
    path = tmp_path / 'usage.db'
    with sqlite3.connect(path) as conn:
        conn.execute(OLD_SESSIONS)  # predates context and canonical_model columns
        conn.execute(OLD_SYNC_LOG)
        conn.execute("INSERT INTO sessions (session_id, source, model, date, input_tokens) "
                     "VALUES ('s1', 'claude_cli', 'm', '2026-09-01', 42)")
        conn.execute("INSERT INTO sync_log VALUES ('s1', 'claude_cli', 'm', 'supabase', '2026-09-02 00:00:00')")
        conn.execute("INSERT INTO sync_log VALUES ('gone', 'claude_cli', 'm', 'supabase', '2026-09-02 00:00:00')")
    store = SqliteStore(path)
    SqliteStore(path)  # second run is a no-op
    assert _rows(path) == [('s1', '2026-09-01', 42)]
    assert store.unsynced_for('supabase') == []
    with sqlite3.connect(path) as conn:
        pk = {r[1]: r[5] for r in conn.execute('PRAGMA table_info(sessions)')}
        log = conn.execute('SELECT session_id, date FROM sync_log').fetchall()
    assert pk['date'] > 0
    assert log == [('s1', '2026-09-01')]
```

Also change `tests/test_models.py::test_key_is_session_source_model` to:

```python
def test_key_is_session_source_model_date():
    r = _rec(session_id="abc", source="copilot_cli", model="gpt-4o", date="2026-10-08")
    assert r.key == ("abc", "copilot_cli", "gpt-4o", "2026-10-08")
```

Append to `tests/test_daily_reporting.py`:

```python
def test_report_groups_day_rows_into_one_session_row(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([
        _rec('s1', '2026-10-08', input_tokens=100, turns=2, tool_calls=1, context_peak_tokens=90,
             start_ts='2026-10-08T09:00:00', end_ts='2026-10-08T10:00:00'),
        _rec('s1', '2026-10-09', input_tokens=50, turns=1, tool_calls=3, context_peak_tokens=120,
             start_ts='2026-10-09T09:00:00', end_ts='2026-10-09T11:00:00')])
    rows = json.loads(UsageReporter(path).report(period='all', as_json=True))['rows']
    assert len(rows) == 1
    r = rows[0]
    assert (r['input_tokens'], r['turns'], r['tool_calls'], r['context_peak_tokens']) == (150, 3, 4, 120)
    assert (r['start_ts'], r['end_ts']) == ('2026-10-08T09:00:00', '2026-10-09T11:00:00')
    detailed = json.loads(UsageReporter(path).report(detailed=True, as_json=True))['rows']
    assert len(detailed) == 2
    assert _summary(path, 'custom', '2026-10-09', '2026-10-09')['total_tokens'] == 50
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python3 -m pytest tests/test_sqlite_daily_rows.py tests/test_models.py tests/test_daily_reporting.py -q`
Expected: FAIL — key is a 3-tuple; second day row overwrites the first; migration leaves the old key; `unsynced_for` returns only the unsynced model row.

- [ ] **Step 3: Widen the record key in `src/models.py`**

```python
    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.session_id, self.source, self.model, self.date)


def merge_records(records: list[SessionRecord]) -> list[SessionRecord]:
    """Deduplicate by (session_id, source, model, date). Last writer wins."""
    merged: dict[tuple[str, str, str, str], SessionRecord] = {}
    for rec in records:
        merged[rec.key] = rec
    return list(merged.values())
```

- [ ] **Step 4: New schema constants in `src/stores/sqlite.py`**

Change the key lines of the two `CREATE` statements:

```python
    PRIMARY KEY (session_id, source, model, date)
```

```python
_CREATE_SYNC_LOG = """
CREATE TABLE IF NOT EXISTS sync_log (
    session_id  TEXT NOT NULL,
    source      TEXT NOT NULL,
    model       TEXT NOT NULL,
    date        TEXT NOT NULL,
    store_name  TEXT NOT NULL,
    synced_at   TEXT NOT NULL,
    PRIMARY KEY (session_id, source, model, date, store_name)
)
"""
```

Replace `_UPSERT` with:

```python
_SESSION_COLUMNS = (
    "session_id", "source", "model", "canonical_model", "date", "start_ts", "end_ts",
    "project", "turns", "tool_calls", "input_tokens", "output_tokens",
    "cache_creation_tokens", "cache_read_tokens", "context_peak_tokens",
    "reasoning_tokens", "context",
)

_INSERT = (
    f"INSERT INTO sessions ({', '.join(_SESSION_COLUMNS)}) "
    f"VALUES ({', '.join('?' * len(_SESSION_COLUMNS))})"
)
```

- [ ] **Step 5: Add the key migration**

In `_migrate`, call the rebuild after the `context` / `canonical_model` column checks and after the ledger drops, right before `conn.commit()`:

```python
            self._migrate_daily_key(conn)
```

Add the method to `SqliteStore`:

```python
    @staticmethod
    def _migrate_daily_key(conn: sqlite3.Connection) -> None:
        """Rebuild pre-daily tables so `date` is part of the primary key.

        Existing rows keep their data and date. Sync entries whose session row
        no longer exists are dropped.
        """
        session_pk = {r[1]: r[5] for r in conn.execute("PRAGMA table_info(sessions)")}
        log_cols = {r[1] for r in conn.execute("PRAGMA table_info(sync_log)")}
        if session_pk.get("date") and "date" in log_cols:
            return
        conn.commit()  # DDL above ran in autocommit; start one explicit transaction
        conn.execute("BEGIN")
        if not session_pk.get("date"):
            cols = ", ".join(_SESSION_COLUMNS)
            conn.execute("ALTER TABLE sessions RENAME TO sessions_pre_daily")
            conn.execute(_CREATE_SESSIONS)
            conn.execute(f"INSERT INTO sessions ({cols}) SELECT {cols} FROM sessions_pre_daily")
            conn.execute("DROP TABLE sessions_pre_daily")
        if "date" not in log_cols:
            conn.execute("ALTER TABLE sync_log RENAME TO sync_log_pre_daily")
            conn.execute(_CREATE_SYNC_LOG)
            conn.execute("""
                INSERT OR IGNORE INTO sync_log (session_id, source, model, date, store_name, synced_at)
                SELECT l.session_id, l.source, l.model, s.date, l.store_name, l.synced_at
                FROM sync_log_pre_daily l
                JOIN sessions s
                  ON s.session_id = l.session_id AND s.source = l.source AND s.model = l.model
            """)
            conn.execute("DROP TABLE sync_log_pre_daily")
        conn.commit()
```

- [ ] **Step 6: Replace-per-session upsert**

Replace `upsert` in `SqliteStore` with:

```python
    def upsert(self, records: list[SessionRecord]) -> int:
        """Replace each collected session's day rows.

        Records are grouped by (session_id, source). When a session's stored
        rows differ from the new set (a day added, removed, or changed), all of
        its rows are replaced and its sync_log entries cleared, so
        unsynced_for() re-pushes the whole session. Unchanged sessions are not
        touched.

        Args:
            records: List of SessionRecord objects to store.

        Returns:
            Count of records received.
        """
        if not records:
            return 0
        sessions: dict[tuple[str, str], dict[tuple, tuple]] = {}
        for r in records:
            sessions.setdefault((r.session_id, r.source), {})[r.key] = tuple(
                getattr(r, c) for c in _SESSION_COLUMNS)
        cols = ", ".join(_SESSION_COLUMNS)
        with closing(self._connect()) as conn, conn:
            for (session_id, source), rows in sessions.items():
                stored = {tuple(row) for row in conn.execute(
                    f"SELECT {cols} FROM sessions WHERE session_id = ? AND source = ?",
                    (session_id, source))}
                if stored == set(rows.values()):
                    continue
                conn.execute("DELETE FROM sync_log WHERE session_id = ? AND source = ?",
                             (session_id, source))
                conn.execute("DELETE FROM sessions WHERE session_id = ? AND source = ?",
                             (session_id, source))
                conn.executemany(_INSERT, rows.values())
        return len(records)
```

- [ ] **Step 7: Key sync tracking on `date`**

In `unsynced_for`, return every row of any session that has at least one unsynced row. Remote stores replace whole sessions, so a partial push would delete the synced rows remotely and never resend them. Replace the `FROM ... WHERE` part of `_UNSYNCED` with:

```sql
        FROM sessions s
        WHERE EXISTS (
            SELECT 1 FROM sessions u
            LEFT JOIN sync_log l
                ON u.session_id = l.session_id
                AND u.source = l.source
                AND u.model = l.model
                AND u.date = l.date
                AND l.store_name = ?
            WHERE u.session_id = s.session_id AND u.source = s.source
              AND l.session_id IS NULL
        )
```

In `mark_synced`, change the statement and parameters to:

```python
        _MARK_SYNCED = """
        INSERT OR IGNORE INTO sync_log (session_id, source, model, date, store_name, synced_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """
```

```python
                [(r.session_id, r.source, r.model, r.date, store_name) for r in records],
```

In `src/report.py` `FullDumpView`, add `AND l.date = sessions.date` after `AND l.model = sessions.model` in the `synced` subquery.

- [ ] **Step 8: Run focused tests, then the full suite**

Run: `python3 -m pytest tests/test_sqlite_daily_rows.py tests/test_models.py tests/test_daily_reporting.py tests/test_sqlite_resync.py tests/test_store_report.py -q`
Expected: PASS.

Run: `python3 -m pytest -q`
Expected: PASS. (Supabase still uses the old conflict key until Task 8, and its test still expects it.)

- [ ] **Step 9: Commit**

```bash
git add src/models.py src/stores/sqlite.py src/report.py tests/test_sqlite_daily_rows.py tests/test_models.py tests/test_daily_reporting.py
git commit -m "feat!: key session rows by local day" -m "BREAKING CHANGE: sessions and sync_log primary keys now include date; existing databases are rebuilt on first run."
```

---

### Task 5: Claude collector emits day rows

**Files:**
- Modify: `src/collectors/claude_cli.py:27-140`
- Modify: `tests/test_claude_cli_collector.py` (`test_since_filter_excludes_old_session`, append tests)

**Interfaces:**
- Consumes: `to_date(ts) -> date | None`, `to_local_iso(ts) -> str | None` from `src/collectors/base.py`.
- Produces: `ClaudeCliCollector.collect(since)` yields one record per local day with assistant activity; `_parse_session(path) -> list[SessionRecord]`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_claude_cli_collector.py`:

```python
def test_session_spanning_two_days_yields_one_row_per_day(tmp_path):
    _write_session(tmp_path, "s1", [
        _asst("2026-10-08T10:00:00Z", "claude-sonnet-4-6", 100, 10),
        _asst("2026-10-08T11:00:00Z", "claude-sonnet-4-6", 200, 20),
        _asst("2026-10-09T10:00:00Z", "claude-sonnet-4-6", 50, 5),
    ])
    records = sorted(ClaudeCliCollector(tmp_path).collect(date(2026, 10, 1)), key=lambda r: r.date)
    assert [(r.date, r.input_tokens, r.output_tokens, r.turns, r.context_peak_tokens)
            for r in records] == [("2026-10-08", 300, 30, 2, 220), ("2026-10-09", 50, 5, 1, 55)]
    assert records[0].start_ts.startswith("2026-10-08")


def test_old_session_touched_recently_yields_all_days(tmp_path):
    _write_session(tmp_path, "s1", [
        _asst("2026-09-01T10:00:00Z", "m", 100, 0),
        _asst("2026-10-09T10:00:00Z", "m", 50, 0),
    ])
    records = list(ClaudeCliCollector(tmp_path).collect(date(2026, 10, 9)))
    assert sorted((r.date, r.input_tokens) for r in records) == [("2026-09-01", 100), ("2026-10-09", 50)]


def test_untimed_assistant_usage_lands_on_start_day(tmp_path):
    untimed = _asst("2026-10-08T10:00:00Z", "m", 7, 0)
    del untimed["timestamp"]
    _write_session(tmp_path, "s1", [_asst("2026-10-08T10:00:00Z", "m", 100, 0), untimed])
    records = list(ClaudeCliCollector(tmp_path).collect(date(2026, 10, 1)))
    assert [(r.date, r.input_tokens, r.turns) for r in records] == [("2026-10-08", 107, 2)]
```

Replace `test_since_filter_excludes_old_session` so it excludes by file age, not start date:

```python
def test_since_filter_excludes_old_session(tmp_path):
    import os
    _write_session(tmp_path, "s-old", [_asst("2026-06-01T10:00:00.000Z", "claude-sonnet-4-6", 100, 50)])
    old = (tmp_path / "proj-1" / "s-old.jsonl")
    stamp = datetime(2026, 6, 1, 12).timestamp()
    os.utime(old, (stamp, stamp))
    records = list(ClaudeCliCollector(tmp_path).collect(date(2026, 7, 3)))
    assert records == []
```

Add `from datetime import date, datetime` at the top (replacing `from datetime import date`).

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python3 -m pytest tests/test_claude_cli_collector.py -q`
Expected: the three new tests FAIL (one record per session; old-start session filtered).

- [ ] **Step 3: Implement per-day parsing**

In `src/collectors/claude_cli.py`, add after the imports:

```python
_COUNTERS = ("turns", "tool_calls", "input_tokens", "output_tokens",
             "cache_creation_tokens", "cache_read_tokens", "context_peak_tokens")
```

Replace `collect` and `_parse_session` with:

```python
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
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `python3 -m pytest tests/test_claude_cli_collector.py -q`
Expected: PASS. If an older test asserts `len(records) == 1` for a single-day fixture, it still holds; if one asserts `start_ts`/`end_ts` across user and assistant entries on one day, the values are unchanged because `bounds` includes every timed entry.

- [ ] **Step 5: Commit**

```bash
git add src/collectors/claude_cli.py tests/test_claude_cli_collector.py
git commit -m "feat(claude): emit one record per active day"
```

---

### Task 6: Codex collector emits day rows

**Files:**
- Modify: `src/collectors/codex_cli.py`
- Delete: `src/usage.py`
- Rename + modify: `tests/test_usage.py` → `tests/test_codex_usage_accounting.py`
- Modify: `tests/test_codex_cli_collector.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: in `src/collectors/codex_cli.py`: `UsageEvent` (frozen dataclass, unchanged fields), `normalize_usage(usage: dict) -> dict[str, int]`, `event_time(timestamp: str, tz=None) -> tuple[str, str, int]`, `AMBIGUOUS_DESCENDANT_USAGE: str`, `CodexScan` (frozen dataclass: `sessions`, `events`, `tools`, `diagnostics` tuples), `CodexCliCollector.scan(since) -> CodexScan`, `CodexCliCollector.collect(since) -> Iterator[SessionRecord]` (day rows; prints diagnostics to stderr).

- [ ] **Step 1: Move the accounting tests**

```bash
git mv tests/test_usage.py tests/test_codex_usage_accounting.py
```

In `tests/test_codex_usage_accounting.py`, change every `from src.usage import ...` to `from src.collectors.codex_cli import ...`, and delete any test that references `UsageCoverage` or `CollectionBatch`.

- [ ] **Step 2: Write failing day-row tests**

In `tests/test_codex_cli_collector.py`, replace `test_resumed_session_splits_usage_across_days` with:

```python
def test_resumed_session_splits_usage_across_days(tmp_path):
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-09-01T12:00:00Z', cwd='/synthetic/project', source='vscode')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-09T03:59:59Z', 100),
        usage_row('r2', '2026-10-09T04:00:00Z', 50)]
    write_rollout(tmp_path, rows)
    collector = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit'))
    records = sorted(collector.collect(date(2026,10,8)), key=lambda r: r.date)
    assert [(r.session_id, r.date, r.input_tokens, r.turns) for r in records] == [
        ('s1','2026-10-08',100,1), ('s1','2026-10-09',50,1)]
```

Append:

```python
def test_tool_calls_are_counted_on_their_own_day(tmp_path):
    rows = [metadata(), context(), usage_row('r1','2026-10-08T12:01:00Z',100),
        dict(type='response_item', timestamp='2026-10-09T12:00:00Z',
             payload=dict(type='function_call', call_id='c1')),
        usage_row('r2','2026-10-09T12:01:00Z',50)]
    write_rollout(tmp_path, rows)
    records = sorted(CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit'))
                     .collect(date(2026,10,8)), key=lambda r: r.date)
    assert [(r.date, r.tool_calls) for r in records] == [('2026-10-08',0), ('2026-10-09',1)]


def test_session_without_usage_yields_one_zero_row_on_start_day(tmp_path):
    write_rollout(tmp_path, [metadata(), context()])
    records = list(CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect(date(2026,10,8)))
    assert [(r.date, r.input_tokens, r.output_tokens) for r in records] == [('2026-10-08',0,0)]


def test_collect_prints_diagnostics(tmp_path, capsys):
    write_rollout(tmp_path, [metadata(), context(), snapshot(100), snapshot(150,2)])
    list(CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect(date(2026,10,8)))
    assert 'baseline' in capsys.readouterr().err
```

- [ ] **Step 3: Convert the remaining Codex tests to `scan()`**

Apply these exact rewrites throughout `tests/test_codex_cli_collector.py`:

| Old | New |
|---|---|
| `.collect_batch(` | `.scan(` |
| `batch.coverage[0].status == 'measured'` / `== ('partial' if missing_id else 'measured')` | `not batch.diagnostics` / `bool(batch.diagnostics) == missing_id` |
| `batch.coverage[0].status == 'partial'` | `batch.diagnostics` |
| `batch.coverage[0].status == 'unavailable'` | `not batch.events` |
| `next(c for c in batch.coverage if c.session_id=='parent').status == 'partial'` | `any('parent' in d for d in batch.diagnostics)` |
| `batch.coverage == ()` | `batch.sessions == ()` |
| `batch.sessions[0].input_tokens == N` / `sum(r.input_tokens for r in batch.sessions) == N` | `sum(r.input_tokens for r in CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect(date(2026,10,8))) == N` |
| `next(r for r in batch.sessions if r.session_id=='parent').input_tokens == 0` | `sum(r.input_tokens for r in CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect(date(2026,10,8)) if r.session_id=='parent') == 0` |

In `test_cumulative_baselines_and_unavailable_usage`, replace the trailing `if coverage:` block with:

```python
    if coverage == 'partial':
        assert batch.diagnostics
    elif coverage == 'measured':
        assert not batch.diagnostics
```

In `test_model_switch_and_tool_call_deduplication`, the assertion over `batch.sessions` `(model, input_tokens, turns, tool_calls, context_peak_tokens)` becomes an assertion over `sorted(collector.collect(...), key=lambda r: r.model)` with the same tuples (all fixture rows are on 2026-10-08).

`batch.events`, `batch.diagnostics`, and `{r.session_id for r in batch.sessions}` assertions stay as written.

- [ ] **Step 4: Run tests and verify they fail**

Run: `python3 -m pytest tests/test_codex_cli_collector.py tests/test_codex_usage_accounting.py -q`
Expected: FAIL — `scan` / `CodexScan` / moved helpers do not exist; `collect` yields lifetime rows.

- [ ] **Step 5: Move the accounting helpers into the collector**

In `src/collectors/codex_cli.py`, replace the `from ..usage import ...` line and the existing `from dataclasses import replace` / `from datetime import ...` / `from typing import Iterator` lines with:

```python
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone, tzinfo
import sys
from typing import Iterator, Literal
```

Then paste, below the imports, `AMBIGUOUS_DESCENDANT_USAGE`, `UsageEvent`, `normalize_usage`, and `event_time` verbatim from `src/usage.py` (drop the inner `from datetime import timezone` in `event_time`; it is now imported at the top). Do not copy `UsageCoverage` or `CollectionBatch`. Add:

```python
@dataclass(frozen=True)
class CodexScan:
    """Deduplicated Codex usage for the selected rollouts, before day aggregation."""
    sessions: tuple[SessionRecord, ...] = ()   # zero-usage base per (session, model), dated on the start day
    events: tuple[UsageEvent, ...] = ()
    tools: tuple[tuple[str, str, str, str], ...] = ()  # (session_id, call_id, model, day)
    diagnostics: tuple[str, ...] = ()
```

Then: `git rm src/usage.py`.

- [ ] **Step 6: Replace `collect` / `collect_batch` with `collect` / `scan`**

```python
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
```

- [ ] **Step 7: Return a `CodexScan` from `_parse`**

In `_parse`:

1. Replace both `return CollectionBatch(diagnostics=...)` with `return CodexScan(diagnostics=...)` (same arguments).
2. Record each tool call's day:

```python
                if isinstance(call_id,str) and call_id:
                    tools.setdefault(call_id,(current_model,self._day(row,start_day)))
```

3. Replace everything from `status='partial' if issues ...` to the end of `_parse` with:

```python
        models=dict.fromkeys(e.model for e in owned.values()) or {current_model:None}
        bases=tuple(SessionRecord(sid,self.source,model=model,date=start_day,start_ts=start,end_ts=start,
            project=project,canonical_model=normalize_model(model,self.source)) for model in models)
        return CodexScan(bases,tuple(owned.values()),
            tuple((sid,call_id,model,day) for call_id,(model,day) in tools.items()),
            tuple(f'codex_cli [{sid}]: {r}' for r in issues))
```

- [ ] **Step 8: Day aggregation helpers**

Replace `_summary` and add `_day` and `_day_records`:

```python
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
```

- [ ] **Step 9: Run tests and verify they pass**

Run: `python3 -m pytest tests/test_codex_cli_collector.py tests/test_codex_usage_accounting.py -q`
Expected: PASS.

Run: `grep -rn "src.usage\|from \.\.usage\|collect_batch\|CollectionBatch\|UsageCoverage" src tests`
Expected: no output.

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add -A src/collectors/codex_cli.py src/usage.py tests/test_codex_cli_collector.py tests/test_codex_usage_accounting.py tests/test_usage.py
git commit -m "feat(codex): emit one record per active day"
```

---

### Task 7: Copilot collector emits day rows

**Files:**
- Modify: `src/collectors/copilot_cli.py`
- Modify: `tests/test_cli_collector.py` (append)

**Interfaces:**
- Consumes: `to_date`, `to_local_iso` from `src/collectors/base.py`.
- Produces: `CopilotCliCollector._query_daily_usage(conn) -> dict[str, list[sqlite3.Row]]`; `_from_daily(rows, session_id, date_str, project, tool_calls) -> Iterator[SessionRecord]`; module helper `_utc(ts: str) -> str`.

- [ ] **Step 1: Verify which usage rows match Copilot's shutdown totals (read-only, user's machine)**

Ask the user for permission first; this reads their local Copilot data and prints only counts.

```bash
python3 - <<'EOF'
import json, pathlib, sqlite3
home = pathlib.Path.home() / ".copilot"
conn = sqlite3.connect(f"file:{home / 'session-store.db'}?immutable=1", uri=True)
rows = conn.execute("""
    SELECT session_id, model,
           SUM(input_tokens), SUM(output_tokens),
           SUM(CASE WHEN agent_id IS NULL THEN input_tokens ELSE 0 END),
           SUM(CASE WHEN agent_id IS NULL THEN output_tokens ELSE 0 END)
    FROM assistant_usage_events GROUP BY session_id, model""").fetchall()
tally = {"all_rows": 0, "main_only": 0, "neither": 0, "no_shutdown": 0}
for sid, model, i_all, o_all, i_main, o_main in rows:
    path = home / "session-state" / sid / "events.jsonl"
    metrics = None
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "session.shutdown":
                metrics = ((event.get("data") or event).get("modelMetrics") or {}).get(model)
    if metrics is None:
        tally["no_shutdown"] += 1
        continue
    usage = metrics.get("usage") or metrics
    want = (usage.get("inputTokens", 0), usage.get("outputTokens", 0))
    tally["all_rows" if want == (i_all, o_all) else "main_only" if want == (i_main, o_main) else "neither"] += 1
print(tally)
EOF
```

Decision:
- `all_rows` is the largest count → implement as written below (all rows count toward tokens).
- `main_only` is the largest → add `AND agent_id IS NULL` to the `WHERE` in `_query_daily_usage` and change the subagent test expectation in Step 2 to `(..., 1000, ...)` totals excluding the agent row.
- `neither` is the largest → stop and report the tally to the user before writing code.

Also tell the user whether shutdown `inputTokens` equals the cache-inclusive table sum: if so, the existing shutdown fallback stores cache-inclusive input — a pre-existing issue to raise as a separate follow-up, not fixed here.

- [ ] **Step 2: Write failing tests**

Append to `tests/test_cli_collector.py`:

```python
def _add_timed_usage(home: Path, rows: list[tuple]) -> None:
    """rows: (session_id, agent_id, model, created_at, input, output, cache_read, cache_write)"""
    conn = sqlite3.connect(home / "session-store.db")
    conn.execute("""
        CREATE TABLE assistant_usage_events (
            session_id TEXT, turn_index INTEGER, agent_id TEXT, model TEXT,
            input_tokens INTEGER, output_tokens INTEGER,
            cache_read_tokens INTEGER, cache_write_tokens INTEGER,
            reasoning_tokens INTEGER, created_at TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO assistant_usage_events VALUES (?, 0, ?, ?, ?, ?, ?, ?, 0, ?)",
        [(s, a, m, i, o, cr, cw, ts) for s, a, m, ts, i, o, cr, cw in rows],
    )
    conn.commit()
    conn.close()


def test_usage_events_split_session_by_day(tmp_path):
    home = _make_home(tmp_path)
    _add_session(home, "s1", "/work/x", "owner/x",
                 "2026-10-08T10:00:00.000Z", "2026-10-09T11:00:00.000Z")
    _add_timed_usage(home, [
        ("s1", None, "model-a", "2026-10-08 10:00:00", 1000, 50, 600, 100),
        ("s1", None, "model-a", "2026-10-09T10:00:00Z", 500, 20, 0, 0),
    ])
    _write_events(home, "s1", [
        {"type": "tool.execution_complete", "timestamp": "2026-10-09T10:00:05Z",
         "data": {"model": "model-a"}},
        _shutdown({"model-a": {"turns": 2, "input": 1500, "output": 70}}),
    ])
    records = sorted(CopilotCliCollector(home).collect(date(2026, 10, 9)), key=lambda r: r.date)
    assert [(r.date, r.input_tokens, r.cache_read_tokens, r.cache_creation_tokens,
             r.output_tokens, r.turns, r.tool_calls, r.context_peak_tokens) for r in records] == [
        ("2026-10-08", 300, 600, 100, 50, 1, 0, 1050),
        ("2026-10-09", 500, 0, 0, 20, 1, 1, 520),
    ]


def test_subagent_usage_counts_tokens_but_not_turns_or_peak(tmp_path):
    home = _make_home(tmp_path)
    _add_session(home, "s1", "/work/x", "owner/x",
                 "2026-10-08T10:00:00.000Z", "2026-10-08T11:00:00.000Z")
    _add_timed_usage(home, [
        ("s1", None, "model-a", "2026-10-08 10:00:00", 1000, 50, 0, 0),
        ("s1", "agent-1", "model-a", "2026-10-08 10:05:00", 9000, 900, 0, 0),
    ])
    _write_events(home, "s1", [_shutdown({"model-a": {"turns": 1, "input": 10000, "output": 950}})])
    [r] = list(CopilotCliCollector(home).collect(date(2026, 10, 8)))
    assert (r.input_tokens, r.output_tokens, r.turns, r.context_peak_tokens) == (10000, 950, 1, 1050)
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `python3 -m pytest tests/test_cli_collector.py -q`
Expected: the two new tests FAIL (one shutdown-total record on the start date).

- [ ] **Step 4: Implement**

Add after the imports in `src/collectors/copilot_cli.py`:

```python
def _utc(ts: str) -> str:
    """assistant_usage_events.created_at defaults to SQLite datetime('now'): naive UTC."""
    if ts.endswith("Z") or "+" in ts[10:]:
        return ts
    return ts.replace(" ", "T") + "Z"
```

In `collect()`:

1. After `peaks = self._query_context_peaks(conn)` add `daily = self._query_daily_usage(conn)`.
2. Replace the start-date filter with selection by recent activity:

```python
            session_date = to_date(start_ts)
            if session_date is None:
                continue
            # Select by recent activity so a resumed old session is updated.
            if (to_date(end_ts) or session_date) < since:
                continue
```

3. Pass the session's rows: `yield from self._parse_events(session_id, date_str, start_iso, end_iso, project, peaks, daily.get(session_id, []))`.

Add the query:

```python
    @staticmethod
    def _query_daily_usage(conn: sqlite3.Connection) -> dict[str, list[sqlite3.Row]]:
        """Timestamped per-request usage, grouped by session.

        Returns {} when the table or its created_at column is absent (older CLI
        versions); sessions then fall back to totals on their start date.
        """
        try:
            rows = conn.execute("""
                SELECT session_id, model, agent_id, created_at,
                       COALESCE(input_tokens, 0)       AS input_tokens,
                       COALESCE(output_tokens, 0)      AS output_tokens,
                       COALESCE(cache_read_tokens, 0)  AS cache_read_tokens,
                       COALESCE(cache_write_tokens, 0) AS cache_write_tokens,
                       COALESCE(reasoning_tokens, 0)   AS reasoning_tokens
                FROM assistant_usage_events
                WHERE created_at IS NOT NULL
            """).fetchall()
        except sqlite3.OperationalError:
            return {}
        by_session: dict[str, list[sqlite3.Row]] = {}
        for r in rows:
            by_session.setdefault(r["session_id"], []).append(r)
        return by_session
```

In `_parse_events`:

1. Add parameter `daily: list[sqlite3.Row]` after `peaks`.
2. Next to `tool_calls_by_model`, add `tool_calls_by_day: dict[tuple[str, str], int] = {}`.
3. In the `tool.execution_complete` branch, after incrementing `tool_calls_by_model`, add:

```python
                tool_day = to_date(event.get("timestamp"))
                day_key = (tool_model, tool_day.isoformat() if tool_day else date_str)
                tool_calls_by_day[day_key] = tool_calls_by_day.get(day_key, 0) + 1
```

4. Immediately after the scan loop, before `if shutdown_payload is not None:`, add:

```python
        if daily:
            yield from self._from_daily(daily, session_id, date_str, project, tool_calls_by_day)
            return
```

Add the builder:

```python
    def _from_daily(
        self, rows: list[sqlite3.Row], session_id: str, date_str: str,
        project: str | None, tool_calls: dict[tuple[str, str], int],
    ) -> Iterator[SessionRecord]:
        buckets: dict[tuple[str, str], dict] = {}
        for r in rows:
            ts = _utc(r["created_at"])
            day = to_date(ts)
            key = (r["model"] or UNKNOWN_MODEL, day.isoformat() if day else date_str)
            b = buckets.setdefault(key, dict(
                turns=0, input_tokens=0, output_tokens=0, cache_read_tokens=0,
                cache_creation_tokens=0, reasoning_tokens=0, context_peak_tokens=0,
                first=ts, last=ts))
            # input_tokens includes cache reads and writes; store the uncached part.
            b["input_tokens"] += max(
                r["input_tokens"] - r["cache_read_tokens"] - r["cache_write_tokens"], 0)
            b["output_tokens"] += r["output_tokens"]
            b["cache_read_tokens"] += r["cache_read_tokens"]
            b["cache_creation_tokens"] += r["cache_write_tokens"]
            b["reasoning_tokens"] += r["reasoning_tokens"]
            if r["agent_id"] is None:  # main conversation only, matching _query_context_peaks
                b["turns"] += 1
                b["context_peak_tokens"] = max(
                    b["context_peak_tokens"], r["input_tokens"] + r["output_tokens"])
            b["first"], b["last"] = min(b["first"], ts), max(b["last"], ts)
        for (model, day), b in sorted(buckets.items()):
            first, last = b.pop("first"), b.pop("last")
            yield SessionRecord(
                session_id=session_id, source=self.source, model=model, date=day,
                start_ts=to_local_iso(first), end_ts=to_local_iso(last), project=project,
                tool_calls=tool_calls.get((model, day), 0), **b,
            )
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python3 -m pytest tests/test_cli_collector.py -q`
Expected: PASS. Existing tests using `_add_usage_events` (no `created_at` column) keep the shutdown path because `_query_daily_usage` returns `{}`.

- [ ] **Step 6: Commit**

```bash
git add src/collectors/copilot_cli.py tests/test_cli_collector.py
git commit -m "feat(copilot): emit one record per active day"
```

---

### Task 8: Supabase replaces sessions remotely

**Files:**
- Modify: `src/stores/supabase.py`
- Modify: `tests/test_supabase_store.py`
- Create: `docs/migrations/2026-10-12-daily-session-rows.sql`

**Interfaces:**
- Consumes: `SessionRecord.key` (4-tuple) from Task 4.
- Produces: `SupabaseStore.upsert(records) -> int` deletes each pushed session's remote rows (chunks of `_DELETE_CHUNK = 100` ids per source), then upserts with `on_conflict="session_id,source,model,date"`.

- [ ] **Step 1: Write failing tests**

In `tests/test_supabase_store.py`, change `test_upsert_uses_conflict_key`'s expectation to `"session_id,source,model,date"`, add `from unittest.mock import call` to the imports, and append:

```python
def test_upsert_deletes_pushed_sessions_before_upsert():
    mock_client = MagicMock()
    with patch("src.stores.supabase._create_client", return_value=mock_client):
        _make_store().upsert([_rec("s1"), _rec("s2"), _rec("s1", source="codex_cli")])
    table = mock_client.table.return_value
    assert [name for name, *_ in table.mock_calls if name in ("delete", "upsert")] == [
        "delete", "delete", "upsert"]
    eq = table.delete.return_value.eq
    assert eq.call_args_list == [call("source", "claude"), call("source", "codex_cli")]
    assert eq.return_value.in_.call_args_list == [
        call("session_id", ["s1", "s2"]), call("session_id", ["s1"])]


def test_large_push_deletes_in_chunks():
    mock_client = MagicMock()
    with patch("src.stores.supabase._create_client", return_value=mock_client):
        _make_store().upsert([_rec(f"s{i}") for i in range(250)])
    in_ = mock_client.table.return_value.delete.return_value.eq.return_value.in_
    assert [len(c.args[1]) for c in in_.call_args_list] == [100, 100, 50]
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python3 -m pytest tests/test_supabase_store.py -q`
Expected: the conflict-key test and the two new tests FAIL.

- [ ] **Step 3: Implement**

In `src/stores/supabase.py`, add a module constant after the imports:

```python
_DELETE_CHUNK = 100  # session ids per delete request; keeps the request URL bounded
```

In `upsert`, after `rows` is built and before the existing upsert call, add:

```python
        # Replace whole sessions: drop their remote day rows first so days removed
        # by a re-collect don't linger. Not atomic over REST — if the upsert below
        # fails, the rows stay unsynced locally and the next collect/sync repairs it.
        by_source: dict[str, list[str]] = {}
        for r in records:
            ids = by_source.setdefault(r.source, [])
            if r.session_id not in ids:
                ids.append(r.session_id)
        for source, session_ids in by_source.items():
            for i in range(0, len(session_ids), _DELETE_CHUNK):
                (self._client.table(self._table).delete()
                    .eq("source", source).in_("session_id", session_ids[i:i + _DELETE_CHUNK])
                    .execute())
```

Change the conflict key to `on_conflict="session_id,source,model,date"`.

- [ ] **Step 4: Create `docs/migrations/2026-10-12-daily-session-rows.sql`**

```sql
-- Apply manually in the Supabase SQL editor BEFORE running a TokenTracer
-- version that stores daily session rows. Default table name below; adapt it
-- if stores.supabase.table is customized.
-- Re-keys token_usage so one session stores one row per local day.
-- Existing rows stay valid: each becomes the row for its current date.
BEGIN;
DO $$
DECLARE c record;
BEGIN
  FOR c IN
    SELECT con.conname
    FROM pg_constraint con
    WHERE con.conrelid = 'public.token_usage'::regclass
      AND con.contype IN ('p', 'u')
      AND (SELECT array_agg(a.attname::text ORDER BY a.attname)
           FROM pg_attribute a
           WHERE a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey))
          = ARRAY['model', 'session_id', 'source']
  LOOP
    EXECUTE format('ALTER TABLE public.token_usage DROP CONSTRAINT %I', c.conname);
  END LOOP;
END $$;
ALTER TABLE public.token_usage
  ADD CONSTRAINT token_usage_session_day_key UNIQUE (session_id, source, model, date);
COMMIT;
-- Verify: SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--         WHERE conrelid = 'public.token_usage'::regclass;
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python3 -m pytest tests/test_supabase_store.py -q`
Expected: PASS.

Run: `python3 -m pytest -q`
Expected: PASS (whole suite).

- [ ] **Step 6: Commit**

```bash
git add src/stores/supabase.py tests/test_supabase_store.py docs/migrations/2026-10-12-daily-session-rows.sql
git commit -m "feat(supabase)!: replace sessions by day key" -m "BREAKING CHANGE: apply docs/migrations/2026-10-12-daily-session-rows.sql before syncing."
```

---

### Task 9: End-to-end check and documentation

**Files:**
- Create: `tests/test_daily_rows_e2e.py`
- Modify: `CLAUDE.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN-HISTORY.md`, `changelog.md`, `docs/superpowers/specs/2026-10-08-codex-daily-usage-design.md` (superseded note)

**Interfaces:**
- Consumes: everything above.
- Produces: documentation only.

- [ ] **Step 1: Write the end-to-end test**

```python
import json
import sqlite3
from datetime import date

from src.collectors import ClaudeCliCollector, CodexCliCollector
from src.dashboard import queries
from src.middleware import ModelNormalizeMiddleware
from src.pipeline import TrackerPipeline
from src.stores.sqlite import SqliteStore


def _claude(root):
    folder = root / 'claude' / 'p'
    folder.mkdir(parents=True)
    (folder / 'c1.jsonl').write_text('\n'.join(json.dumps(e) for e in [
        {"type": "assistant", "timestamp": "2026-10-08T10:00:00Z",
         "message": {"model": "claude-sonnet-4-6", "usage": {"input_tokens": 100, "output_tokens": 10}}},
        {"type": "assistant", "timestamp": "2026-10-09T10:00:00Z",
         "message": {"model": "claude-sonnet-4-6", "usage": {"input_tokens": 50, "output_tokens": 5}}},
    ]), encoding='utf-8')
    return root / 'claude'


def _codex(root):
    rollout = root / 'codex' / 'sessions' / 'r.jsonl'
    rollout.parent.mkdir(parents=True)
    rollout.write_text(''.join(json.dumps(r) + '\n' for r in [
        dict(type='session_meta', payload=dict(id='x1', timestamp='2026-10-08T10:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        dict(type='token_usage_record', timestamp='2026-10-09T10:00:00Z', payload=dict(
            session_id='x1', thread_id='x1', turn_id='t1', response_id='r1',
            usage=dict(input_tokens=70, output_tokens=7))),
    ]), encoding='utf-8')
    return root / 'codex'


def test_collect_twice_keeps_daily_totals(tmp_path):
    claude, codex, db = _claude(tmp_path), _codex(tmp_path), tmp_path / 'usage.db'

    def run():
        return (TrackerPipeline().since(date(2026, 10, 1))
                .add(ClaudeCliCollector(claude)).add(CodexCliCollector(codex))
                .middlewares(ModelNormalizeMiddleware()).stores(SqliteStore(db)).run())

    run()
    run()
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        day8 = queries.summary(conn, 'custom', '2026-10-08', '2026-10-08')
        day9 = queries.summary(conn, 'custom', '2026-10-09', '2026-10-09')
        rows = [tuple(r) for r in conn.execute('SELECT source, date FROM sessions ORDER BY source, date')]
    assert (day8['total_tokens'], day9['total_tokens']) == (110, 132)
    assert (day8['session_count'], day9['session_count']) == (1, 2)
    assert rows == [('claude_cli', '2026-10-08'), ('claude_cli', '2026-10-09'), ('codex_cli', '2026-10-09')]
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest tests/test_daily_rows_e2e.py -q`
Expected: PASS (all behavior already implemented). If it fails, fix the owning task's code, not the test.

- [ ] **Step 3: Full verification**

Run: `python3 -m pytest -q`
Expected: PASS.

Run: `cd frontend && node --test tests/usage.test.mjs && npm run build -- --outDir /private/tmp/tokentracer-frontend-build`
Expected: tests PASS; build succeeds. Do not commit build output.

- [ ] **Step 4: Update documentation**

- `CLAUDE.md`:
  - Sync: `unsynced_for` returns whole sessions (all day/model rows) when any row is unsynced.
  - Architecture tree: remove `usage.py` and `stores/sqlite_usage.py`; describe `claude_cli.py`, `codex_cli.py`, `copilot_cli.py` as yielding one record per `(session, model, local day)`; describe `SqliteStore` as "daily rows; replace-per-session upsert; sync tracking".
  - Key invariants: merge key `(session_id, source, model, date)`; `upsert` replaces all rows of each collected `(session_id, source)` and clears that session's `sync_log` when anything changed.
  - UsageStore schema: new primary keys; automatic one-time rebuild of pre-daily databases.
  - Claude/Copilot data details: per-day bucketing rules (Claude: assistant `timestamp`, untimed → start day; Copilot: `assistant_usage_events.created_at` as UTC, cache-exclusive input, fallback to shutdown totals on start date); selection by recent activity.
  - Replace the "Codex ledger and reporting" section with a short "Daily rows and reporting" section: reports/dashboard read `sessions`; session views aggregate day rows; `--detailed` shows raw day rows; Codex dedup rules still apply in memory; partial/ambiguous usage surfaces as collect-time warnings.
  - Supabase: conflict key `session_id,source,model,date`; delete-then-upsert; apply `docs/migrations/2026-10-12-daily-session-rows.sql` first; third-party stores that only `upsert` may keep stale day rows.
- `README.md`: same user-facing points (daily rows, migration step, backfill limited to logs still on disk; Claude keeps ~30 days by default).
- `docs/ARCHITECTURE.md`: replace ledger sections with the daily-row flow.
- `docs/DESIGN-HISTORY.md`: add an entry dated 2026-10-12: event ledger replaced by daily session rows, and why (simplicity; accepted loss of event-level protections).
- `changelog.md` under `## [Unreleased]`: `### Changed` (daily rows, Supabase key, selection by recent activity), `### Removed` (usage-event ledger, `usage_table` store option, attribution notices). Note that a leftover `usage_table` key in `[stores.supabase]` must be removed from the user's config.
- `docs/superpowers/specs/2026-10-08-codex-daily-usage-design.md`: add a first line `> Superseded by 2026-10-12-daily-session-rows-design.md.`

- [ ] **Step 5: Commit**

```bash
git add tests/test_daily_rows_e2e.py CLAUDE.md README.md docs changelog.md
git commit -m "docs: document daily session rows"
```

- [ ] **Step 6: Hand off the remote migration**

Tell the user: apply `docs/migrations/2026-10-12-daily-session-rows.sql` in the Supabase SQL editor before the next `collect`/`sync`, and confirm the backup from Task 1 exists. Do not run it yourself.
