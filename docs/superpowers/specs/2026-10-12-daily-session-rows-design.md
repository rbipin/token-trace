# Daily session rows (replace the usage-event ledger)

## Goal

Record token usage per local calendar day in the existing `sessions` table instead of a separate event ledger. One row per `(session_id, source, model, date)`. A session that runs on October 8 and 9 produces two rows; its lifetime total is the sum of its rows.

This replaces the `codex-support` branch's event ledger (`usage_events`, `usage_coverage`, event sync logs, `usage_daily` / `reporting_usage` views, and the remote `token_usage_events` table). That ledger was never applied to Supabase.

## Agreed decisions

1. **Key:** `sessions` primary key becomes `(session_id, source, model, date)`. Same for `sync_log` (plus `store_name`) and the remote `token_usage` conflict key.
2. **Sources:** Claude, Codex, and Copilot all split by day. If a source gives only a session total, the whole total goes on the session's start date.
3. **Columns are per day:** `turns`, `tool_calls`, `start_ts`, `end_ts`, `context_peak_tokens`, and token counts describe that day only. Session-level values are aggregates: `SUM` for counts, `MIN(start_ts)`, `MAX(end_ts)`, `MAX(context_peak_tokens)`. `project`, `context`, and `canonical_model` repeat on each row.
4. **Re-collect replaces per session:** each collect deletes all stored rows of a selected `(session_id, source)` and inserts the fresh day rows, in one transaction. Accepted edge case: if a source shortens a log file but keeps it, lost days disappear. Sessions whose logs are deleted are never selected again, so their rows remain.
5. **Existing data is kept:** each existing row becomes a day row on its current `date`, unchanged. Logs that still exist are re-split by the next collect.
6. **Backup first:** copy the local db to `<db>.bak-2026-10-12` before the first run of the new code.
7. **Remote replace:** Supabase deletes a session's remote rows, then upserts its fresh rows. *(Recommended; confirm during spec review.)*

Accepted trade-offs: event-level protections are gone (response-ID dedup across runs, preserved day assignment after timezone changes, protection against shortened re-imports). Codex `partial` / `unavailable` coverage markers are gone; those conditions remain visible as collect-time warnings only.

## Data model

```sql
CREATE TABLE sessions (
    session_id, source, model, canonical_model, date, start_ts, end_ts, project,
    turns, tool_calls, input_tokens, output_tokens, cache_creation_tokens,
    cache_read_tokens, context_peak_tokens, reasoning_tokens, context,
    PRIMARY KEY (session_id, source, model, date)
);
sync_log PRIMARY KEY (session_id, source, model, date, store_name)
```

`date` is the local calendar day (machine timezone at collect time) of the activity. `SessionRecord.key` becomes `(session_id, source, model, date)`; `merge_records` dedups on that key.

### Local migration (automatic, idempotent, one transaction)

Detect the old key with `PRAGMA table_info(sessions)` (`date` has `pk = 0`). Then:

1. Create `sessions_new` with the new key; `INSERT ... SELECT` all rows; drop `sessions`; rename.
2. Same for `sync_log` with `date` filled from the matching `sessions` row. Sync entries with no matching session are dropped.
3. `DROP VIEW IF EXISTS reporting_usage, usage_daily`; `DROP TABLE IF EXISTS usage_events, usage_coverage, usage_event_sync_log, usage_coverage_sync_log`.

Pre-existing additive column checks (`context`, `canonical_model`) run before step 1.

### Remote migration

New file `docs/migrations/2026-10-12-daily-session-rows.sql`, applied manually by the user to `token_usage`: drop the current primary key / unique constraint on `(session_id, source, model)` and add `UNIQUE (session_id, source, model, date)` (the upsert conflict target; works whether or not the table has another primary key). Existing rows stay valid. Delete `docs/migrations/2026-10-08-usage-events.sql`.

## Collectors

All collectors keep the `ActivityCollector` protocol (`collect(since) -> Iterable[SessionRecord]`) and emit day rows. **Selection is by recent activity** (file mtime, or Copilot `updated_at`/`endedAt`), not start date, and a selected session always yields **all** its days, because the store replaces the whole session.

- **Claude** (`claude_cli.py`): bucket each assistant message by the local date of its `timestamp`. Per bucket: token sums, `turns`, `tool_calls`, context peak, first/last timestamp. Messages without a timestamp go to the session's start day; a session with no timestamps at all uses today (current behavior). Drop the start-date `since` filter; keep the mtime filter.
- **Codex** (`codex_cli.py`): keep the current parsing, response-ID / fingerprint dedup, fork ownership rules, and snapshot-delta logic, all in memory. Replace `_summary` with a per-day aggregation of the deduplicated `UsageEvent`s. Tool calls are bucketed by the timestamp of their `function_call` row. A session with no usage yields one zero-token row on its start date (metadata only). Ambiguous-parent sessions keep their existing exclusion: snapshot deltas dropped, warning emitted. Remove `collect_batch` and `CollectionBatch`; `UsageEvent` becomes a module-private helper type or is moved into the collector.
- **Copilot** (`copilot_cli.py`): when `assistant_usage_events` exists and has rows for the session, bucket them by local date of `created_at` (stored as UTC) per model. `input_tokens` is cache-inclusive, so uncached input = `input_tokens - cache_read_tokens - cache_write_tokens`. Context peak per day = `MAX(input_tokens + output_tokens)` over `agent_id IS NULL` rows (existing convention). `turns` per day = count of `agent_id IS NULL` rows (one per main-conversation request); `tool_calls` from `tool.execution_complete` timestamps. Otherwise fall back to today's logic (shutdown `modelMetrics` or summed `assistant.message`), with the whole total on the start date.

**Open uncertainty (Copilot):** it is not verified whether the sum of `assistant_usage_events` rows (including `agent_id` subagent rows) equals the shutdown `modelMetrics` totals. The plan includes a read-only comparison the user runs on their machine; if they differ, include/exclude `agent_id` rows to match `modelMetrics` before shipping.

## Pipeline and stores

- `TrackerPipeline.run()` returns to the session-only flow: collect → `merge_records` → middleware → `SqliteStore.upsert` → remote push / `run_sync`. Remove event plumbing (`events_written`, `process_events`, `upsert_batch`).
- `SqliteStore.upsert(records)`: group by `(session_id, source)`. For each group in one transaction: read existing rows; if the existing row set differs from the new set (any row added, removed, or changed), delete all `sync_log` rows for that session. Delete all `sessions` rows for that session, insert the new ones. This keeps every row of a changed session unsynced together.
- `unsynced_for` / `mark_synced` join and key on `date` too. `unsynced_for` returns every row of a session that has any unsynced row, because remote stores replace whole sessions (migrated databases can hold sessions where only some models are synced).
- `SupabaseStore.upsert(records)`: for each distinct `(session_id, source)` in the batch, `delete().eq(session_id).eq(source)`, then upsert all rows with `on_conflict="session_id,source,model,date"`. Not atomic over REST: if the upsert fails after the delete, the rows stay unsynced locally and the next `collect` / `sync` repairs the remote. Remove `usage_table`, `upsert_events`, `upsert_session_batch`, `supports_usage_events`.
- Third-party stores that only implement `upsert` get the new rows but keep stale day rows; documented limitation.
- `run_sync` returns to its session-only form (no event or coverage branches).
- Remove `src/stores/sqlite_usage.py`, `UsageEventStore`, `BatchActivityCollector`, and `src/usage.py` items no longer used (`normalize_usage` and `event_time` move to the Codex collector if only it uses them).

## Reporting and dashboard

- `src/report.py` and `src/dashboard/queries.py` read `sessions` directly instead of `reporting_usage`. Period filters apply to `date`, so tokens are scoped by usage day.
- Session counts use distinct `(source, session_id)`.
- Default and `--summary` session views group day rows by `(session_id, source, model)` within the period: sums for counts, `MIN(start_ts)`, `MAX(end_ts)`, `MAX(context_peak_tokens)`. A session spanning two periods appears in both, with each period's share.
- `--detailed` shows raw day rows (all columns + sync status).
- Remove the `attribution()` query, `UsageAttribution.jsx`, and its use in `TokensPage.jsx` and frontend tests.

## Error handling

- Malformed log lines: skipped with the existing per-collector warnings; other sessions continue.
- Local migration runs in one transaction; on failure nothing changes and the backup remains.
- Remote push failure: warning, rows stay unsynced, retried by the next `collect` or `sync`.

## Testing

Synthetic fixtures and temp databases only.

- Model: `SessionRecord.key` and `merge_records` include `date`.
- Migration: old-schema db with sessions, sync_log, and ledger tables migrates to the new key, keeps rows and sync state, drops ledger objects, and is idempotent.
- Store: replace-per-session removes stale days; changed sessions lose all their sync entries; unchanged sessions keep theirs.
- Claude: one file spanning two local days → two rows with correct per-day tokens, turns, tool calls, peak, timestamps; old session resumed today is selected by mtime and yields all days.
- Codex: existing scenario tests adapted to assert day rows; duplicates across active/archive and fork copies still counted once; no-usage session → one zero row.
- Copilot: `assistant_usage_events` spanning two days → two rows per model with cache-exclusive input; table absent → shutdown totals on start date.
- Supabase: delete-then-upsert per session with the new conflict key (mocked client).
- Report/dashboard: day-scoped totals, distinct session counts, per-period aggregation of lifetime columns.
- Frontend: `node --test tests/usage.test.mjs` after removing attribution UI.

## Documentation

After verified implementation: update `CLAUDE.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN-HISTORY.md`, and `changelog.md`. Mark `2026-10-08-codex-daily-usage-design.md` as superseded by this spec.

## Out of scope

- Applying the Supabase migration (the user applies it).
- Per-day attribution for logs that no longer exist.
