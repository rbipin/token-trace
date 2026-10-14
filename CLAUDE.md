# CLAUDE.md — ai-token-tracer

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Implementation workflow

Always use the writing-plans skill for implementation plans and follow its usual
test-first sequence: write a failing test, run it and verify the expected failure,
implement the smallest change, run focused tests and verify they pass, then commit
code and tests together. Update documentation after verified implementation.

## Commands

```bash
# Run all tests
python3 -m pytest -q

# Run a single test file
python3 -m pytest tests/test_claude_cli_collector.py -q

# Collect usage data (idempotent)
python3 tracker.py collect --lookback 3

# Report usage
# Default: today's usage grouped by session/model (Project Source Model Start End Input Output Reasoning CacheRead CacheCreate CacheHit% CtxPeak Turns Tools)
python3 tracker.py report

# --summary: compact session view (Session Project Date Start End Turns Tokens CacheHit%)
python3 tracker.py report --summary

# --summary + period: aggregated roll-up grouped by period+model
python3 tracker.py report --summary --period month
python3 tracker.py report --summary --period year
python3 tracker.py report --summary --period all     # entire database, no date filter

# --by-project: group by stored project identity (real name, guid, or whimsical mask)
python3 tracker.py report --summary --period all --by-project

# --period scopes all views: all | day | month | year  (default: day)
python3 tracker.py report --period month             # detailed sessions for current month
python3 tracker.py report --period all --by-project  # all projects ever

# Filter and JSON output
python3 tracker.py report --model claude-sonnet-4-6
python3 tracker.py report --summary --period month --json

# --detailed: all rows in the db, all 17 columns, sync status (overrides --summary/--by-project, ignores --period)
python3 tracker.py report --detailed

# Configuration
python3 tracker.py config set track_project_names whimsical   # yes | no | whimsical
python3 tracker.py config set context work   # label this machine's usage ("work"/"personal")

# List local project identities (project key → guid → whimsical name; never synced)
python3 tracker.py projects

# Schedule the daily collector natively (macOS launchd / Windows Task Scheduler)
python3 tracker.py schedule 23:50    # registers/replaces a daily "collect --lookback 1" job
python3 tracker.py unschedule        # removes it

# Sync unsynced records to configured remote stores (e.g., Supabase)
python3 tracker.py sync
python3 tracker.py sync --dry-run   # show pending counts without pushing

# Run the local dashboard (frontend is pre-built and committed by CI; see README)
python3 tracker.py dashboard
python3 tracker.py dashboard --daemon
python3 tracker.py dashboard --stop
```

No build step — standard library only at runtime. Install `pytest` for testing: `pip install -r requirements.txt`.

**Packaging**: `pyproject.toml` defines the `tokentracer` console script. Install locally with `pipx install .` or `uv tool install .`. Default db path when installed: `~/.tokentracer/usage.db`.

`tracker.py schedule <HH:MM>` / `tracker.py unschedule` (`src/commands/schedule.py`, `src/schedule.py`) natively register/remove the collector as a scheduled task (Windows Task Scheduler / macOS launchd) — no separate scripts required.

## Architecture

The tracker follows an **Open/Closed pipeline**: adding a new data source only requires implementing the `ActivityCollector` protocol and registering it in `_build_pipeline()` in `src/commands/collect.py`. No other module needs to change.

```
tracker.py               CLI entry point — builds argparse from the command registry and dispatches
src/
  commands/              Command pattern + static registry: one module per subcommand
    base.py              Command protocol (name, help, configure(parser), run(args) -> int)
    __init__.py          COMMANDS registry list (add new commands here)
    collect.py           CollectCommand (+ _build_pipeline / _build_stores helpers); after the pipeline run, sweeps any still-unsynced records via common.run_sync()
    report.py            ReportCommand
    config.py            ConfigCommand (owns its own set sub-dispatch)
    projects.py          ProjectsCommand
    schedule.py           ScheduleCommand / UnscheduleCommand — native daily "collect --lookback 1" job (see src/schedule.py)
    sync.py              SyncCommand, using common.run_sync() for its push/retry logic
    common.py            load_remote_stores helper + run_sync(sqlite_store, remote_stores, dry_run) core push/retry logic, shared by collect and sync
  schedule.py             OS-native scheduling helpers: parse_time, resolve_executable, plus macOS (launchd) and Windows (Task Scheduler) schedule_*/unschedule_* functions
  models.py              SessionRecord frozen dataclass (has canonical_model field); merge_records deduplicates by (session_id, source, model, date)
  middleware/            Pluggable RecordMiddleware chain (Pipes-and-Filters), run in TrackerPipeline.run() after merge_records, before upsert
    base.py              RecordMiddleware Protocol: name, applies(records) -> bool, process(records) -> list[SessionRecord]
    model_normalize.py   ModelNormalizeMiddleware — always applies; sets canonical_model via normalize_model()
  model_normalize.py     normalize_model(raw, source): strip -YYYYMMDD suffix -> alias lookup in model_aliases.toml -> passthrough
  model_aliases.toml     Static alias table, keyed by [source] then raw model string -> canonical name. Loaded from ~/.tokentracer/model_aliases.toml if present, else the bundled copy in this directory — lets users add/override aliases without a package release
  project_identity.py    ProjectIdentityStore (local-only project-key→guid→whimsical table; keys are repo slugs or folder names, never full paths) + ProjectNameResolver (tri-state naming policy)
  repo_identity.py       resolve_repo_slug(cwd): walks up to .git, parses origin remote from config -> owner/repo (read-only, cached, never raises)
  collectors/
    base.py              ActivityCollector protocol + to_date / to_local_iso helpers
    codex_cli.py         Reads active/archive Codex rollouts in memory (response accounting, cumulative-delta fallback); yields one record per (session, model, local day); ambiguity surfaces as collect warnings
    copilot_cli.py       Reads session-store.db + events.jsonl from ~/.copilot/; yields per-(session, model, local day) records
    claude_cli.py        Reads ~/.claude/projects/**/*.jsonl; yields one record per (session, local day) with assistant activity
  whimsy/                Standalone docker-style name generator (stdlib-only, extractable to its own repo; only public API is generate_name)
  stores/
    __init__.py          SessionStore Protocol (name attr + upsert + close)
    registry.py          load_store_registry() (entry-point discovery + built-in fallback), instantiate_store()
    sqlite.py            SqliteStore — local SQLite sink; daily rows, replace-per-session upsert, whole-session sync tracking
    supabase.py          SupabaseStore — remote sink; upserts into a Supabase token_sessions table
  store.py               Deprecated alias for SqliteStore (kept for backward compat)
  pipeline.py            Fluent TrackerPipeline; runs collectors in parallel via ThreadPoolExecutor; .middlewares(*mw) registers the RecordMiddleware chain run in run(); a successful remote-store push also marks the record synced in the local store's sync_log (via mark_synced, duck-typed so pipeline.py never imports SqliteStore) — a mark_synced failure is reported separately and does not count as a push failure
  config.py              Paths, TOML loading (Config.load()), write_toml_setting(), _expand_env_vars(), ensure_user_config_seeded() (called once from tracker.py main(); seeds ~/.tokentracer/model_aliases.toml and .tokentracer.toml from bundled defaults on first run, since installed builds get no pip post-install hook)
  report.py              UsageReporter: all/day/month/year periods, cache efficiency header, default detailed session view includes Reasoning, CtxPeak, and Tools columns, --summary, --by-project, --detailed (all rows + all columns + Synced from sync_log)
```

**Data flow**: `Collector.collect(since)` → `List[SessionRecord]` → `merge_records` deduplicates → RecordMiddleware chain transforms (e.g. `ModelNormalizeMiddleware` sets `canonical_model`) → `UsageStore.upsert` writes SQLite → `UsageReporter.report` aggregates for display.

**Key invariants**:
- `collect` is always idempotent — re-running replaces each collected session's rows. Merge key is `(session_id, source, model, date)`.
- Upsert **replaces** all stored rows of each collected `(session_id, source)` in one transaction and clears that session's `sync_log` entries when anything changed. There is no summation across runs.
- Collectors are **read-only** with respect to their source files — they must never write to them.

**UsageStore schema**: `sessions` table with PRIMARY KEY `(session_id, source, model, date)` (one row per local day; `sync_log` adds `date` to its key; databases created before daily rows are rebuilt automatically on first connect). On first connect, if an old `usage` / `daily_activity` table exists it is dropped with a warning and the user is asked to re-collect. A separate local-only `project_identities` table stores normalized project key → guid → whimsical-name mappings and is never queried by sync code.

**Config file**: `~/.tokentracer/.tokentracer.toml`. `[tracking]` supports `track_project_names` as a string enum: `"yes"` (real name), `"no"` (stable 12-hex guid per project (repo slug or folder name); default), or `"whimsical"` (stable docker-style masked name). Project identity is keyed by git repo slug (`owner/repo` — from the Copilot session `repository` column, or by reading `<cwd>/.git/config` origin remote for Claude sessions), falling back to the cwd folder name; full paths are never stored. Two clones of the same repo therefore map to one project. `yes` mode displays the full slug (e.g. `rbipin/TokenTrace`). `tracker.py config set track_project_names <value>` validates against that enum; invalid or legacy boolean TOML values warn and fall back to `"no"`. The `collect` CLI overrides it per run with `--project-mode <yes|no|whimsical>`. `[tracking]` also supports `context` (string, default `"personal"`) — a usage-context label (e.g. `"work"`) stamped on every collected `SessionRecord` via `TrackerPipeline.context()` and stored in the `context` column of the `sessions` table (and pushed to remote stores); CLI flag `--context <label>` on `collect` overrides it per run. `[stores.<name>]` sections declare remote stores (see below); `${VAR}` placeholders in string values are expanded at instantiation time — lookup order is `os.environ` first, then `~/.tokentracer/.tokentracer.env` (simple `KEY=VALUE` file, `#` comments, optional quotes). Missing vars raise `ValueError`.

## Stores registry (remote sinks)

Stores implement the `SessionStore` Protocol in `src/stores/__init__.py` (`name: str` class attr, `upsert(records) -> int`, `close()`). The local `SqliteStore` is always active; remote stores are optional and driven by `tokentracer sync`:

- **Discovery**: `load_store_registry()` in `src/stores/registry.py` discovers stores via the `tokentracer.stores` entry-point group (declared in `pyproject.toml`). When the package isn't installed (repo checkout), it falls back to the built-ins: `sqlite` and `supabase`.
- **Instantiation**: `instantiate_store(name, params, class_path=None)` expands `${VAR}` env placeholders in `params`, then constructs the store — via `class_path` (dotted import path, bypasses the registry) if given, else by registry name.
- **Sync flow**: `tracker.py sync` reads `[stores.*]` from `~/.tokentracer/.tokentracer.toml`, and for each remote store pushes rows the SqliteStore reports as unsynced (`unsynced_for(store_name)`), then marks them synced per store. `--dry-run` prints pending counts only. Failed stores are reported without blocking others; stores are always closed in a `finally`. This push/retry logic lives in `run_sync()` (`src/commands/common.py`), shared by `sync` and by `collect`'s post-run sweep below.
- **Collect also syncs**: `tracker.py collect` pushes freshly-collected records to remote stores inline as part of the pipeline run (`TrackerPipeline.run()`), marking each successful push synced immediately. After that, if any remote stores are configured, `collect` calls `run_sync()` once more to sweep and retry anything still marked unsynced — records whose remote push failed in this run or a prior one. In steady state (no failures) the sweep finds nothing pending and prints nothing; it only surfaces output (`Synced N pending record(s) to <store>`, or a `Warning [<store>]: ...` on failure) when there's something to report. This means the scheduled task (registered via `tracker.py schedule`, which only ever calls `collect`) is self-healing without a second scheduled sync job.

**Built-in remote store — Supabase** (`src/stores/supabase.py`): upserts rows into a `token_sessions` table with `on_conflict="session_id,source,model,date"` (mirrors the local primary key). Before upserting it deletes each pushed session's remote rows (chunks of 100 ids) so days dropped by a re-collect do not linger; apply `docs/migrations/2026-10-12-daily-session-rows.sql` first. Third-party stores that only implement `upsert` may keep stale day rows. Lazy client creation on first upsert; requires optional dep `supabase>=2.0` (`pip install tokentracer[supabase]`). The upserted payload includes `tool_calls`, `reasoning_tokens`, and `context_peak_tokens`; the remote `token_sessions` table must have those bigint columns. Configure with:

```toml
[stores.supabase]
url = "${SUPABASE_URL}"
key = "${SUPABASE_KEY}"      # service role key (bypasses RLS)
table = "token_sessions"     # optional, this is the default
```

### Adding a new store

1. Create `src/stores/<name>.py` with a class implementing `SessionStore` (`name` class attr + `upsert` + `close`). Keep third-party imports optional (try/except at module level, raise a helpful `ImportError` on first use).
2. Register it under `[project.entry-points."tokentracer.stores"]` in `pyproject.toml` (and add it to the built-in fallback in `registry.py` if it ships with this repo).
3. Add any third-party dep as an optional extra in `[project.optional-dependencies]`.
4. Add tests under `tests/` mocking the client (see `tests/test_supabase_store.py`).
5. Users enable it with a `[stores.<name>]` section in `~/.tokentracer/.tokentracer.toml`; external packages can also provide stores via the same entry-point group — no code changes here needed.

**Copilot CLI data details**: newer CLI versions nest event payloads under a `data` key and use `created_at`/`updated_at` session columns (older: `startedAt`/`endedAt`) — the collector supports both. Completed sessions write a `session.shutdown` event with `modelMetrics` (per-model token breakdown; counts flat in old format, under `usage` + `requests.count` in new). Active sessions fall back to summing `outputTokens` from `assistant.message` events (new format exposes only output tokens there; full input/cache counts arrive at shutdown). Each `(session_id, model, local day)` becomes one `SessionRecord`. `tool.execution_complete` events are counted into `tool_calls`, attributed per model via each event's `model` field when a shutdown event exists, and summed to the single detected model otherwise; the event scan no longer stops at `session.shutdown`. `context_peak_tokens` is computed by a bulk `MAX(input_tokens + output_tokens)` query over the `assistant_usage_events` table in `session-store.db` with `agent_id IS NULL` (`input_tokens` is cache-inclusive); if the table is absent, `context_peak_tokens` defaults to `0` without warning. When `assistant_usage_events` has `created_at` rows for a session (naive UTC, converted to the local day), records are built from those rows per (model, day) with cache-exclusive input (`input_tokens - cache_read - cache_write`); `agent_id` (subagent) rows add tokens but not turns or context peak. Otherwise the shutdown/`assistant.message` totals land on the session start date. Sessions are selected by recent activity (`updated_at`/`endedAt`), not start date.

**Claude CLI data details**: each conversation is a JSONL file under `~/.claude/projects/<project-id>/<conv-id>.jsonl`. The file stem is the `session_id`. Assistant messages contain `message.usage` with `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`. One `SessionRecord` per (JSONL file, local day), bucketed by each assistant message's `timestamp` (untimed messages go to the session's start day). Files are selected by mtime and a selected file yields all its days. `tool_use` content blocks in assistant messages are counted into `tool_calls`. `context_peak_tokens` is the maximum per-message `input_tokens + cache_read_input_tokens + cache_creation_input_tokens + output_tokens` across that day's assistant messages. `reasoning_tokens` stays `0` (no source field in the JSONL).

**Persisted surfaces only**: Codex editor and CLI sessions are supported through their local rollout files. Web/desktop or other editor surfaces without persisted accounting are outside scope; do not invent a collector from live-only UI telemetry.

**DB default**: `usage.db` next to `tracker.py` (override with `--db`). `Config.paths` uses `Path.home()` for cross-platform compatibility; tests inject synthetic `Paths` via `Config` to stay hermetic.

## Codex and daily rows

`Paths.codex_home` reads `CODEX_HOME` or defaults to `~/.codex`, with explicit
injected paths taking precedence. `CodexCliCollector.scan(since)` selects
active/archive files by local mtime and parses their entire available histories;
`collect()` buckets the deduplicated usage events by local day and yields one
`SessionRecord` per (session, raw model, day). Source identity is `codex_cli`,
displayed as Codex. Preserve raw model names and metadata session IDs.

Deduplication runs in memory on every collect: a response ID (or fingerprint) is
counted once across active/archive copies and forks, response events supersede
snapshot deltas, and a tool call is counted once per call ID on the day of its
row. Explicit descendant metadata can make parent cumulative ownership
ambiguous; those snapshot deltas are dropped and a warning is printed. Unknown
ownership, malformed counts, missing usage, and truncated tails surface as
collect-time warnings rather than guessed dates or totals. A session without
usage yields one zero-token row on its start date.

## Daily rows and reporting

`sessions` holds one row per `(session_id, source, model, date)`; `date` is the
local day of the activity (the start date when a source only has a session
total). Every non-key column describes that day only. Each collect replaces all
rows of every selected `(session_id, source)`, so collectors select by recent
activity (file mtime, or Copilot `updated_at`) and always emit every day of a
selected session. If a source shortens a log, the lost days disappear; sessions
whose logs are deleted keep their stored rows.

Reports and the dashboard read `sessions` directly, and period filters apply to
`date`. Session views group day rows by `(session_id, source, model)` inside the
period (sums for counts, `MIN(start_ts)`, `MAX(end_ts)`,
`MAX(context_peak_tokens)`), so a session spanning two periods appears in both
with each period's share. Count distinct `(source, session_id)` sessions.
Reasoning is part of output; caches are separate from uncached input.
`--detailed` shows raw day rows.

Sync: `unsynced_for` returns every row of any session that has an unsynced row,
because remote stores replace whole sessions.

Use synthetic fixtures and temporary databases; never collect live user data or
apply a remote migration as a test. Frontend render tests run with
`cd frontend && node --test tests/usage.test.mjs`. Build validation can use
`npm run build -- --outDir /private/tmp/tokentracer-frontend-build` to preserve
CI-managed bundled static assets.

## Adding a new collector

1. Create `src/collectors/<name>.py` implementing `ActivityCollector` (`source: str` class attr + `collect(since: date) -> Iterable[SessionRecord]`).
2. Export it from `src/collectors/__init__.py`.
3. Add the relevant path to `Paths` in `src/config.py`.
4. Instantiate it in `_build_pipeline()` in `src/commands/collect.py`.
5. Add tests under `tests/` using `tmp_path` to create fixture files.

Nothing else needs to change.

## Adding a new middleware

1. Implement `RecordMiddleware` (`src/middleware/base.py`): `name: str`, `applies(records) -> bool`, `process(records) -> list[SessionRecord]`.
2. Register it via `.middlewares(...)` on the `TrackerPipeline` where it's built — currently `_build_pipeline()` in `src/commands/collect.py`. Middlewares run in registration order; each one's `applies()` gates whether its `process()` runs.
3. `SessionRecord` is a **frozen dataclass** — `process()` must return new records built with `dataclasses.replace()`, never mutate in place.
4. Add tests under `tests/` covering both `applies()` and `process()`.

See `docs/ARCHITECTURE.md#middleware` for the full design (Pipes-and-Filters) and `ModelNormalizeMiddleware` as the worked example.
