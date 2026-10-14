# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Changes recorded here start with the Codex daily usage implementation.
Earlier releases are documented in the repository's Git tags and release notes.

## [Unreleased]

## [1.0.7] - 2026-10-13

### Added

- Codex CLI and editor usage collection from active and archived local rollouts,
  using `CODEX_HOME` or `~/.codex`.
- Daily session rows: Claude, Codex, and Copilot each store one row per
  `(session, source, model, local day)`, so day, month, and year reports reflect
  the days tokens were used.
- Codex dashboard branding.
- [Supabase migration](docs/migrations/2026-10-12-daily-session-rows.sql) that
  adds `date` to the remote key. Apply it manually before upgrading.
- Project `.mcp.json` that registers the Supabase MCP server for Claude Code.
- Documentation for verifying idempotent collection and repairing missing
  remote rows ([Verifying and repairing sync](docs/ARCHITECTURE.md#verifying-and-repairing-sync)).

### Changed

- `sessions` and `sync_log` primary keys include `date`. Existing databases are
  rebuilt automatically on first run; each old row becomes the row for its
  current date. Back up `usage.db` first.
- Every collect replaces all stored rows of each collected session, and
  collectors select sessions by recent activity instead of start date, so an old
  session resumed today is re-split by day. Logs deleted from disk keep their
  stored rows.
- Supabase upserts use conflict key `session_id,source,model,date` and delete a
  session's remote rows before upserting its fresh day rows. Sync returns every
  row of a session that has any unsynced row.
- Reports and the dashboard read `sessions` directly; session views aggregate
  day rows within the selected period.
- Reasoning tokens display as included in output rather than an extra additive
  category.

### Removed

- The per-event usage ledger (`usage_events`, coverage tables, `usage_daily` and
  `reporting_usage` views), remote event synchronization, the `usage_table`
  Supabase option, and the dashboard attribution notices. These were never
  released. Codex partial or ambiguous usage now appears as collect-time
  warnings. Remove any leftover `usage_table` key from `[stores.supabase]` in
  your config.

### Fixed

- Reporting test fixtures tied to an expired calendar month.
- Custom-range dashboard queries binding extra filter parameters.
- Existing databases failing daily report/dashboard queries before collection
  initialized the additive schema.
- Incomplete UTF-8 rollout tails aborting updates for unrelated sessions.

See the [design history](docs/DESIGN-HISTORY.md) for accounting decisions and
links to the approved design and implementation plan.

[Unreleased]: https://github.com/rbipin/TokenTrace/compare/v1.0.7...HEAD
[1.0.7]: https://github.com/rbipin/TokenTrace/compare/v1.0.6...v1.0.7
