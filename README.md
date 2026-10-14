<h1 align="center">Token Trace</h1>

<p align="center">
  A local, periodic tracker for your AI tool token usage — session summaries from GitHub Copilot, Claude Code, and Codex, plus measured Codex daily usage, stored in SQLite.
</p>

<p align="center">
  <a href="https://github.com/rbipin/TokenTrace/actions/workflows/ci.yml"><img src="https://github.com/rbipin/TokenTrace/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/rbipin/TokenTrace/actions/workflows/release.yml"><img src="https://github.com/rbipin/TokenTrace/actions/workflows/release.yml/badge.svg" alt="Release" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-local--first-003B57?logo=sqlite" />
  <img src="https://img.shields.io/badge/runtime%20deps-stdlib%20only-brightgreen" />
</p>

<br />

<img width="1536" height="800" alt="TokenTrace" src="https://github.com/user-attachments/assets/25f04f4b-ecc8-4b9f-95be-52098c9bffed" />

---

## Overview

<!-- description -->
Token Trace keeps **one row per session, model, and local day**, so day, month, and year reports reflect the days tokens were actually used. Sessions whose logs are no longer on disk keep the single row first recorded for them, dated on their start date.
<!-- /description -->

<!-- purpose -->
I use AI tools heavily from the CLI and noticed that none of the existing AI harnesses — Copilot, Claude Code, etc. — give a meaningful token-level breakdown or trend over time. They show activity in the moment but offer no persistent view of how much you're consuming or how efficiently you're using it. No dashboard exists today that tracks and reports this across tools in one place.

This project is my answer to that gap: a lightweight local collector that pulls token data from the sources that actually persist it to disk, stores it in SQLite, and lets me query it however I want. The goal is to understand my AI token usage and how it trends over time — and eventually use the data for things like a heatmap of usage intensity across days or models.
<!-- /purpose -->

**Built entirely with Claude Code** — requirements, direction, and corrections were provided by me; implementation was handled by Claude.

> **Which surfaces are supported?**
>
> Collection follows locally persisted token data. Copilot CLI writes shutdown
> metrics; Claude Code writes conversation JSONL usage. Codex CLI and editor
> sessions are supported when their rollouts persist accounting records under
> `CODEX_HOME`. Web or desktop sessions without local accounting logs are outside
> the filesystem collector's scope.

---

## Outcome

<!-- outcome -->
This usage analytics tool reports locally recorded token counts per session, model, and tool, along with cache efficiency metrics and estimated cost savings. Key features include:

- Tracks tool calls per session (Copilot tool events / Claude tool_use blocks)
- Tracks context peak — the largest single-request token footprint per session (main conversation only; models used solely by subagents show 0)
- Trend analysis across daily, monthly, and yearly views
- Optional project-level usage breakdowns and context labels (work / personal)
- Idempotent data collection for safe scheduled runs
- Remote synchronization to pluggable backends like Supabase
- Heatmap-ready datasets for future visualization and usage-intensity analysis
<!-- /outcome -->

---

## Tech Stack

<!-- techstack -->
| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Storage | SQLite |
| Config | TOML, .env |
| Testing | pytest |

<!-- /techstack -->

---

## Data Sources

| Source | Location | Metrics |
|---|---|---|
| Copilot CLI | `~/.copilot/session-store.db` + `session-state/<id>/events.jsonl` | sessions, turns, per-model token counts (input, output, cache read/write, reasoning), tool calls, context peak tokens |
| Claude Code CLI | `~/.claude/projects/**/*.jsonl` | per-session token counts (input, output, cache read/write), tool calls, context peak tokens |
| Codex CLI / editor | `${CODEX_HOME:-~/.codex}/sessions/**/*.jsonl` and `archived_sessions/**/*.jsonl` | response usage, measured local days, raw models, caches, reasoning, request footprint, tool calls |

### Daily usage rows

TokenTracer stores one row per `(session, source, model, local day)`. A session
that runs on two days has two rows, and its lifetime total is the sum of its
rows. Copilot, Claude, and Codex all split by day; if a source only reports a
session total, the whole total goes on the session's start date. Each `collect`
re-reads every recently modified log and replaces all stored rows of those
sessions, so an old session resumed today is included by the normal scheduled
`collect --lookback 1`. Logs that no longer exist on disk cannot be re-split, so
history older than your retained logs (Claude keeps about 30 days by default)
stays as it was first recorded.

`CODEX_HOME` overrides `~/.codex`; an explicitly injected `Paths.codex_home`
retains precedence in embedded use. Codex collection discovers both active and
archived rollouts, selects recently modified files, and imports their complete
available histories. Session identity comes from source metadata, so archive
moves and renamed files do not create duplicates.

```bash
tokentracer collect --lookback 30
tokentracer report --period all --summary --json
tokentracer sync --dry-run
```

Input excludes cached input and cache creation, which have their own columns.
Reasoning is included in output and is never added twice. Raw model identity
stays intact; optional `[codex_cli]` aliases affect display only. Explicit
thread ownership prevents copied fork responses from being counted again. When a
known parent has only cumulative accounting and child responses exist, the
parent snapshot ownership is ambiguous: only supported response usage is
reported and `collect` prints a warning.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ — standard library only at runtime (`tomllib` for config) |
| Storage | SQLite — `~/.tokentracer/usage.db`, idempotent upserts, per-store sync tracking |
| Remote stores | Pluggable `SessionStore` protocol via the `tokentracer.stores` entry-point group; Supabase built in (optional extra) |
| Config | TOML — `~/.tokentracer/.tokentracer.toml`, secrets via env vars or `~/.tokentracer/.tokentracer.env` |
| Packaging | `pyproject.toml` console script `tokentracer` — installable with pipx / uv / pip |
| Testing | pytest (`pip install -r requirements.txt`) |

---

## Architecture

The tracker follows an **Open/Closed pipeline**: adding a new data source only requires implementing the `ActivityCollector` protocol and registering it in `tracker.py`. No other module needs to change.

```
Collector.collect(since)          one collector per AI tool surface
  └── List[SessionRecord]         frozen dataclass, one per (session, model)
        └── merge_records         deduplicates by (session_id, source, model)
              └── SqliteStore.upsert   last-write-wins, idempotent
                    └── UsageReporter  day / month / year / all roll-ups
                    └── tokentracer sync → remote stores (e.g. Supabase)
```

**Key invariants:**

- `collect` is always **idempotent** — re-running overwrites existing session rows. Merge key is `(session_id, source, model)`.
- Upsert is **last-write-wins** — no summation across runs.
- Collectors are **read-only** with respect to their source files.

Before records are written, they pass through a pluggable **middleware**
pipeline. Today that's model-name normalization: raw model identifiers
reported differently by each source (e.g. Copilot vs. Claude Code) are
resolved to a stable `canonical_model`, so reports can group and filter by
model regardless of which tool collected the session. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#middleware) for how the
middleware system works and how to add a new one.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture: collect data flow, exact source files and schemas, storage, sync, and extension points. [docs/DESIGN-HISTORY.md](docs/DESIGN-HISTORY.md) records the design decisions that shaped the project. [changelog.md](changelog.md) tracks unreleased changes.

---

## Project Structure

```
TokenTracer/
├─ pyproject.toml            # packaging — pip/pipx/uv entry point, tokentracer.stores entry points
├─ tracker.py                # CLI entry — builds argparse from the command registry and dispatches
├─ src/
│  ├─ commands/              # Command pattern + static registry, one module per subcommand
│  │  ├─ base.py            # Command protocol (name, help, configure(parser), run(args) -> int)
│  │  ├─ __init__.py        # COMMANDS registry list
│  │  ├─ collect.py         # CollectCommand (+ _build_pipeline / _build_stores helpers)
│  │  ├─ report.py          # ReportCommand
│  │  ├─ config.py          # ConfigCommand (owns its own set sub-dispatch)
│  │  ├─ projects.py        # ProjectsCommand
│  │  ├─ sync.py            # SyncCommand (+ _run_sync core logic)
│  │  └─ common.py          # load_remote_stores helper shared by collect/sync
│  ├─ models.py              # SessionRecord (frozen dataclass, has canonical_model) + merge_records
│  ├─ middleware/            # Pluggable RecordMiddleware chain (Pipes-and-Filters)
│  │  ├─ base.py            # RecordMiddleware protocol (name, applies, process)
│  │  └─ model_normalize.py # ModelNormalizeMiddleware — sets canonical_model via normalize_model()
│  ├─ model_normalize.py     # normalize_model(raw, source): strip date suffix -> alias lookup -> passthrough
│  ├─ model_aliases.toml     # Static alias table, keyed by [source] then raw model string
│  ├─ project_identity.py    # ProjectIdentityStore (local-only project-key→guid→whimsical) + ProjectNameResolver
│  ├─ repo_identity.py       # resolve_repo_slug(cwd) — walks up to .git, parses origin remote
│  ├─ collectors/            # one collector per AI tool surface
│  │  ├─ base.py            # ActivityCollector protocol + to_date / to_local_iso helpers
│  │  ├─ codex_cli.py       # Codex CLI/editor — one record per (session, model, local day)
│  │  ├─ copilot_cli.py     # Copilot CLI — one record per (session, model, local day)
│  │  └─ claude_cli.py      # Claude Code CLI — one record per JSONL session
│  ├─ stores/                # pluggable store backends (entry-point registry)
│  │  ├─ __init__.py        # SessionStore protocol
│  │  ├─ registry.py        # store discovery + instantiation (env var expansion)
│  │  ├─ sqlite.py          # SqliteStore — local db, daily rows, replace-per-session upsert, sync tracking
│  │  └─ supabase.py        # SupabaseStore — remote Supabase sink
│  ├─ report.py              # UsageReporter (day/month/year, cache efficiency, --summary, --by-project, --detailed)
│  ├─ pipeline.py            # fluent TrackerPipeline — parallel collectors, .middlewares() chain
│  ├─ config.py              # Paths, TOML loading, write_toml_setting
│  └─ store.py               # deprecated alias for SqliteStore (backward compat)
├─ packages/
│  └─ whimsy/                # Standalone docker-style name generator — own PyPI distribution (Apache-2.0)
├─ tests/                    # pytest suite with fixtures
└─ docs/                     # design docs, ARCHITECTURE.md, DESIGN-HISTORY.md, implementation plans
```

---

## Getting Started

### Prerequisites

- Python 3.11+ (standard library only at runtime)
- `pytest` only for running the tests: `pip install -r requirements.txt`

### Install

The **base package** covers local collection and reporting (`collect` /
`report` / `config` — standard library only). If you want to push records to
a **remote store** (e.g. Supabase via `tokentracer sync`), install with the
store's extra — e.g. `tokentracer[supabase]` — otherwise `collect`/`sync`
will warn that the store's client library is missing.

**From a GitHub Release** (replace `{version}` with the latest release version, without the `v`, for example `X.Y.Z`):

```bash
# uv
uv tool install https://github.com/rbipin/TokenTrace/releases/download/v{version}/tokentracer-{version}-py3-none-any.whl

# pip
pip install https://github.com/rbipin/TokenTrace/releases/download/v{version}/tokentracer-{version}-py3-none-any.whl

# from source at a tag
uv tool install git+https://github.com/rbipin/TokenTrace@v{version}
pip install git+https://github.com/rbipin/TokenTrace@v{version}

# with the Supabase store extra
uv tool install "tokentracer[supabase] @ git+https://github.com/rbipin/TokenTrace@v{version}"
pip install "tokentracer[supabase] @ git+https://github.com/rbipin/TokenTrace@v{version}"
```

To add an extra to an existing uv tool install, re-run with `--force`:

```bash
uv tool install --force "tokentracer[supabase] @ git+https://github.com/rbipin/TokenTrace@v{version}"
```

**From the latest main branch:**

```bash
# pipx (recommended)
pipx install git+https://github.com/rbipin/TokenTrace

# uv
uv tool install git+https://github.com/rbipin/TokenTrace
```

**From source (clone locally):**

```bash
git clone https://github.com/rbipin/TokenTrace
pipx install .          # or: uv tool install .
# with the Supabase store: pipx install ".[supabase]"  /  uv tool install ".[supabase]"
```

### First run

```bash
tokentracer collect
tokentracer report
```

The database is created at `~/.tokentracer/usage.db` on first run. Override with `--db`.

---

## Usage

```bash
# Collect (the scheduled job). Re-scans the last N days and upserts.
python3 tracker.py collect                      # default lookback: 3 days
python3 tracker.py collect --lookback 90        # backfill more history
python tracker.py collect --project-mode whimsical
# project modes: yes = real name, no = stable 12-hex guid per cwd, whimsical = masked docker-style name

# Default report — today's sessions, one row per session, full token detail
python3 tracker.py report
# Columns: Project  Source  Model  Start  End  Input  Output  Reasoning  CacheRead  CacheCreate  CacheHit%  CtxPeak  Turns  Tools

# Scope to a different period (all | day | month | year)
python3 tracker.py report --period month        # this month's sessions, detailed
python3 tracker.py report --period all          # every session in the database

# --summary: compact per-session view (Session Project Date Start End Turns Tokens CacheHit%)
python3 tracker.py report --summary

# --summary + period: aggregated roll-up grouped by period+model
python3 tracker.py report --summary --period month
python3 tracker.py report --summary --period year
python3 tracker.py report --summary --period all

# --by-project: group by project
python3 tracker.py report --by-project                          # today, by project
python3 tracker.py report --summary --period all --by-project   # all history, by project

# Dump every row in the db with all columns and sync status
python3 tracker.py report --detailed

# Filter by model, emit JSON — combinable with any of the above
python3 tracker.py report --period month --model claude-sonnet-4-6
python3 tracker.py report --summary --period all --by-project --json

# List local project identities (cwd -> guid -> whimsical name; never synced)
python3 tracker.py projects

# Schedule the daily collector natively (macOS launchd / Windows Task Scheduler)
python3 tracker.py schedule 23:50    # registers/replaces a daily "collect --lookback 1" job
python3 tracker.py unschedule        # removes it

# Sync unsynced records to configured remote stores (e.g., Supabase)
python3 tracker.py sync
python3 tracker.py sync --dry-run   # show pending counts without pushing

# Configuration (persisted to ~/.tokentracer/.tokentracer.toml)
python tracker.py config set track_project_names whimsical
python3 tracker.py config set context work        # label this machine's usage as "work"
```

The database lives at `~/.tokentracer/usage.db` by default (override with
`--db`). Re-running `collect` is **idempotent** — each session is identified
by its unique ID and re-collecting overwrites the stored row.

### Cache efficiency

Every text report opens with a cache efficiency summary:

```
Cache efficiency: 72% read from cache (~65% cost saved)
```

This is computed across all sessions in the database and shows what fraction of
your total token budget came from the cache, and the approximate cost saving
(cache reads cost ~10% of regular input tokens).

---

## Dashboard

A local web dashboard visualizes `usage.db` without the CLI `report` commands.

The pre-built frontend is committed to the repo by CI (`src/dashboard/static/`,
regenerated automatically on every push to `main` that touches `frontend/`),
so every install method — including `uv tool install git+...` and a plain
source checkout — includes the dashboard out of the box. When contributing,
never build or commit `src/dashboard/static/` by hand; CI overwrites it.
For local frontend development only: `cd frontend && pnpm install && pnpm run build`.

Then:
```bash
tokentracer dashboard              # foreground, http://127.0.0.1:8420, Ctrl-C to stop
tokentracer dashboard --port 9000  # custom port
tokentracer dashboard --daemon     # install as a persistent background service
tokentracer dashboard --stop       # remove the persistent service
```

`--daemon` installs a background service that starts the dashboard on login
and restarts it if it's killed. On Windows, the Scheduled Task is started immediately
after creation (not only at next logon), and re-running `--daemon` reports
`Dashboard daemon already running ...` if the service is already active. On macOS,
it's a `launchd` agent with `RunAtLoad` + `KeepAlive` at `~/Library/LaunchAgents/com.ai-token-tracer.dashboard.plist`;
on Windows, it's a Scheduled Task that runs `ONLOGON`. It's a separate job from the
collector's own schedule (below), so you can run one, the other, or both —
logs go to `~/.tokentracer/dashboard.log`. `--stop` ends a running task before
deleting the service. On macOS, re-running `--daemon` (e.g. with a different `--port`)
replaces it; on Windows, stop the daemon first with `--stop`, then re-run `--daemon`.

---

## Configuration

Settings are stored in `~/.tokentracer/.tokentracer.toml` in your home directory:

| OS | Config file | Env file (secrets) |
| --- | --- | --- |
| macOS / Linux | `~/.tokentracer/.tokentracer.toml` | `~/.tokentracer/.tokentracer.env` |
| Windows | `C:\Users\<you>\.tokentracer\.tokentracer.toml` | `C:\Users\<you>\.tokentracer\.tokentracer.env` |

You can edit the file directly
or use `tracker.py config set <key> <value>` to update individual keys.

```toml
# ~/.tokentracer/.tokentracer.toml

[tracking]
# Project labeling mode stored in sessions.project.
# "yes" = real project/repo name.
# "no" = stable 12-hex guid per cwd (default).
# "whimsical" = stable docker-style masked name like admiring_agnesi.
# Override per-run with: --project-mode {yes,no,whimsical}
track_project_names = "no"

# Usage context label stamped on every collected session record and stored
# in the database (local SQLite and remote stores). Use it to differentiate
# work from personal usage, e.g. set "work" on your work machine.
# Default: "personal". Override per-run with: --context <label>
context = "personal"
```

Set a value from the CLI (rewrites the file safely, preserving other keys):

```bash
python tracker.py config set track_project_names whimsical
python3 tracker.py config set context work
```

`tracker.py config set track_project_names` validates the enum and rejects old
boolean values such as `true` / `false`. If `~/.tokentracer/.tokentracer.toml` still contains
a legacy boolean or any other invalid value, TokenTrace warns and falls back to
`"no"`.

Masked modes keep a local-only `project_identities` table inside `usage.db`
(`cwd_key` case-insensitive → `guid` → `whimsical_name`). Sync never uploads
that table, so remote stores only ever see the already-resolved value stored in
`sessions.project`.

CLI flags `--project-mode <yes|no|whimsical>` and `--context <label>` on the
`collect` subcommand override the file values for that run only.

---

## Remote Stores (sync)

Beyond the local SQLite database, TokenTracer can push session records to
**remote stores** via a pluggable stores registry. Each store implements the
`SessionStore` protocol (`name`, `upsert(records)`, `close()`), and remote
stores are configured with `[stores.<name>]` sections in `~/.tokentracer/.tokentracer.toml`. `${VAR}` placeholders in
values are resolved from environment variables first, then from a
`~/.tokentracer/.tokentracer.env` file (`KEY=VALUE` lines), so secrets never live in the
config file.

Run `tokentracer sync` to push records that haven't been synced to each store
yet (sync state is tracked per store in the local database, so re-running is
cheap and idempotent). Use `--dry-run` to see pending counts first.

### Supabase (built in)

A Supabase store ships with TokenTracer. Install the optional dependency and
configure it:

```bash
pip install "tokentracer[supabase]"     # pulls in supabase-py >= 2.0
```

```toml
# ~/.tokentracer/.tokentracer.toml
[stores.supabase]
url = "${SUPABASE_URL}"
key = "${SUPABASE_KEY}"      # service role key
table = "token_sessions"     # optional, this is the default
```

Create the table once in the Supabase SQL editor:

```sql
create table token_sessions (
  session_id text not null,
  source text not null,
  model text not null,
  canonical_model text,
  date date,
  start_ts timestamptz,
  end_ts timestamptz,
  project text,
  turns integer default 0,
  tool_calls bigint default 0,
  input_tokens bigint default 0,
  output_tokens bigint default 0,
  cache_creation_tokens bigint default 0,
  cache_read_tokens bigint default 0,
  reasoning_tokens bigint default 0,
  context_peak_tokens bigint default 0,
  context text default 'personal',
  unique (session_id, source, model, date)
);
```

If you have an existing `token_sessions` table, add the new columns:

```sql
ALTER TABLE token_sessions ADD COLUMN tool_calls bigint DEFAULT 0;
ALTER TABLE token_sessions ADD COLUMN reasoning_tokens bigint DEFAULT 0;
ALTER TABLE token_sessions ADD COLUMN context_peak_tokens bigint DEFAULT 0;
```

Daily session rows need a remote key that includes `date`. If your table was
created before daily rows, apply
[`docs/migrations/2026-10-12-daily-session-rows.sql`](docs/migrations/2026-10-12-daily-session-rows.sql)
in the Supabase SQL editor **before** upgrading, adapting the table name for
custom configurations. The migration is never applied by collection or
synchronization. When a session changes, TokenTracer deletes that session's
remote rows and upserts the fresh day rows (conflict key
`session_id,source,model,date`). The replace is not atomic over REST: if the
upsert fails, the rows stay unsynced locally and the next `collect` or `sync`
repairs the remote. Remove any leftover `usage_table` key from
`[stores.supabase]`; it is no longer used. No prompt, tool arguments/output,
reasoning text, or raw project path is included in the synchronized payload.

Then:

```bash
# Either set environment variables:
export SUPABASE_URL=https://<project>.supabase.co
export SUPABASE_KEY=<service-role-key>

# ...or put them in ~/.tokentracer/.tokentracer.env (env vars win if both are set):
#   SUPABASE_URL=https://<project>.supabase.co
#   SUPABASE_KEY=<service-role-key>

tokentracer sync --dry-run   # preview
tokentracer sync             # push
```

Rows are upserted with conflict key `(session_id, source, model, date)` — the same
key as the local database — so syncing is idempotent too. Before each push the
store deletes the remote rows of the sessions being pushed (see the Supabase
section above).

If local and remote totals disagree (for example `sync --dry-run` shows 0
pending but remote rows are missing), see
[Verifying and repairing sync](docs/ARCHITECTURE.md#verifying-and-repairing-sync).

### Writing your own store

Stores are discovered through the `tokentracer.stores` entry-point group, so
you can add a new backend (Postgres, S3, an HTTP API, …) without touching
TokenTracer's code:

1. Implement the protocol in your own package:

   ```python
   from src.stores import SessionStore  # Protocol: name, upsert, close

   class MyStore:
       name = "mystore"
       def __init__(self, url: str): ...
       def upsert(self, records) -> int: ...
       def close(self) -> None: ...
   ```

2. Declare the entry point in your package's `pyproject.toml`:

   ```toml
   [project.entry-points."tokentracer.stores"]
   mystore = "my_package.store:MyStore"
   ```

3. Enable it in `~/.tokentracer/.tokentracer.toml` — constructor kwargs come straight from
   the section (with `${VAR}` env expansion):

   ```toml
   [stores.mystore]
   url = "${MYSTORE_URL}"
   ```

Alternatively, skip packaging and point directly at a class with
`class = "my_module.MyStore"` in the store's config section.

---

## Run It Periodically

`collect` is designed to be run on a schedule (it's idempotent, so re-runs
just overwrite the same session rows). `tokentracer schedule <HH:MM>`
registers a daily job that runs `collect --lookback 1` at the given time,
using the OS-native scheduler — `launchd` on macOS, Task Scheduler on
Windows. It auto-detects whether `tokentracer` is on PATH (packaged install)
or falls back to running `tracker.py` from a repo checkout. Safe to re-run:
it silently replaces any existing job.

```bash
tokentracer schedule 23:50    # registers/replaces the daily job
tokentracer unschedule        # removes it
```

**macOS (launchd):** registers `com.ai-token-tracer` as a `launchd` agent.
Output goes to `~/.tokentracer/tracker.log` (or `<repo>/tracker.log` for a
repo checkout).

```bash
launchctl start com.ai-token-tracer   # run once now
launchctl list com.ai-token-tracer    # check status
```

**Windows (Task Scheduler):** registers the `ai-token-tracer` scheduled task.

```powershell
Start-ScheduledTask -TaskName "ai-token-tracer"                       # run once now
(Get-ScheduledTaskInfo -TaskName "ai-token-tracer").LastTaskResult    # check status
```

This is a separate job from the [dashboard daemon](#dashboard) — the two are
installed and removed independently.

---

## Development

```bash
pip install -r requirements.txt
python3 -m pytest -q
```

### Extending

Add a new **surface** by implementing the `ActivityCollector` protocol
(`collect(since: date) -> Iterable[SessionRecord]`) and adding it to the
pipeline in `tracker.py`. Add a new **store backend** by implementing the
`SessionStore` protocol and registering it via the `tokentracer.stores`
entry-point group (see [Writing your own store](#writing-your-own-store)).
No other module needs to change.

### Releasing (maintainers)

Releases are published from the GitHub UI. The tag is the source of truth for
the version; you do not edit `pyproject.toml` by hand.

1. Merge your changes to `main`. Move the `[Unreleased]` entries in
   `CHANGELOG.md` under a new `## [X.Y.Z] - YYYY-MM-DD` heading.
2. Wait for the `Frontend Build` workflow to finish. It may add a
   `Build dashboard frontend [skip ci]` commit to `main`.
3. On GitHub, open **Releases → Draft a new release**.
4. Create the tag `vX.Y.Z` (exactly `v` + three numbers) on `main`. Click
   **Generate release notes**, then click **Publish release**.
5. The `Release` workflow runs on publish. It:
   - runs the tests;
   - builds the frontend;
   - sets `version` in `pyproject.toml` from the tag and builds the wheel and sdist;
   - attaches both files to the release;
   - commits `chore(release): bump version to X.Y.Z [skip ci]` to `main`.

If the workflow does not start, check the **Actions** tab. If the bump commit
cannot push, check the branch protection rules on `main`: they must allow the
`github-actions[bot]` push. The wheel is still attached in that case.

---

## License

Licensed under the [PolyForm Shield License 1.0.0](LICENSE.md) — free to
use, modify, and distribute for any purpose except providing a product or
service that competes with this software.

Required Notice: Copyright Bipin Radhakrishnan (https://github.com/rbipin/TokenTrace)
