# Windows Dashboard Fixes — Design

**Date**: 2026-07-27
**Status**: Approved

## Problem

On Windows, after installing tokentracer v1.0.2 with `uv tool install git+https://...`:

1. `tokentracer dashboard` fails with
   `Error: frontend build not found at ...\site-packages\src\dashboard\static. Run: cd frontend && pnpm install && pnpm run build`.
   Root cause: `src/dashboard/static/` is a Vite build output, gitignored, so a
   git+ (source) install never contains it.
2. `tokentracer dashboard --daemon` on Windows registers a Scheduled Task with
   `/SC ONLOGON` but never starts it, so the dashboard only comes up after the
   next logon. Running it again re-creates the task silently instead of saying
   it's already running.

`tokentracer schedule` was also suspected, but it is by design collector-only
and stays that way — **schedule/unschedule never touch the dashboard daemon**.

## Decisions

- **Distribution**: `uv tool install git+https://...` must work out of the box,
  including the dashboard. Since git+ installs build from the source tree, the
  built frontend (`src/dashboard/static/`) must be committed to the repo.
  A CI workflow auto-builds and commits it on push to `main` — contributors
  never build or commit it by hand.
- **schedule and dashboard daemon stay fully separate.** No cross-wiring in
  either direction.

## Design

### 1. Packaging: CI auto-commits built frontend to main

- Remove `src/dashboard/static/` from `.gitignore`.
- New workflow `.github/workflows/frontend-build.yml`:
  - Trigger: `push` to `main` with `paths: [frontend/**]` (plus
    `workflow_dispatch` for a manual first run / rebuild).
  - Steps: checkout, pnpm/node setup (same as `release.yml`),
    `pnpm install --frozen-lockfile && pnpm run build` in `frontend/`,
    then commit `src/dashboard/static/` back to `main` only if
    `git status --porcelain src/dashboard/static` shows changes.
    Commit as `github-actions[bot]`, message
    `Build dashboard frontend [skip ci]`.
  - Loop safety: the commit touches only `src/dashboard/static/`, which the
    `paths: [frontend/**]` filter never matches, and `[skip ci]` guards other
    workflows. Needs `permissions: contents: write`.
- `release.yml`: keep its frontend build step (it rebuilds from source, which
  is authoritative for wheels) — no change required.
- `src/commands/dashboard.py`: the missing-frontend error can now only mean a
  stale checkout or a fork without the assets; keep the existing pnpm-build
  message but also mention pulling latest `main`.
- README: note that git+ installs include the pre-built dashboard, and that
  `src/dashboard/static/` is CI-generated — never edit or build it by hand
  when contributing (the workflow will overwrite it).

### 2. Windows daemon: start immediately + already-running report

`src/dashboard/daemon.py`:

- `_install_windows(port)`:
  - Before creating, query the task (`schtasks /Query /TN ai-token-tracer-dashboard /FO LIST`).
    If it exists **and** its status is `Running`, report already-running
    (return a signal / raise nothing) so the command prints
    `Dashboard daemon already running at http://127.0.0.1:<port>.` and exits 0.
  - Otherwise `/Create /F` as today, then immediately
    `schtasks /Run /TN ai-token-tracer-dashboard` so the dashboard starts now,
    not at next logon. A `/Run` failure raises `RuntimeError` (surfaced as an
    error by the command).
- `_uninstall_windows()`: `schtasks /End /TN ...` (ignore failures) before
  `/Delete /F`, so `--stop` also stops a currently running dashboard.
- macOS behavior unchanged (`launchctl load` with `RunAtLoad` already starts
  immediately; `unload` already stops it).
- `install()` returns `bool`: `True` = installed/started, `False` = already
  running. `DashboardCommand.run` prints the appropriate message.

### 3. Out of scope

- `tokentracer schedule` / `unschedule` — unchanged.
- CI workflows — unchanged.
- macOS daemon — unchanged apart from `install()` returning `True`.

## Testing

- CI workflow validated by a `workflow_dispatch` run after merge (no unit
  tests for workflows).
- `tests/test_dashboard_daemon.py`:
  - Windows install runs `/Query`, `/Create`, `/Run` (mock `subprocess.run`);
    returns `True`.
  - Windows install with task already `Running` skips create/run, returns `False`.
  - Windows uninstall runs `/End` then `/Delete`; `/End` failure ignored.
  - `/Run` failure raises `RuntimeError`.
- `tests/test_dashboard_command.py`:
  - already-running daemon prints the "already running" message, exit 0.
