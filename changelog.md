# Changelog

Changes recorded here start with the Codex daily usage implementation.
Earlier releases are documented in the repository's Git tags and release notes.

## Unreleased

### Added

- Codex CLI and editor usage collection from active and archived local rollouts,
  using `CODEX_HOME` or `~/.codex`.
- Timestamped usage events, atomic SQLite batch persistence, daily reporting
  views, and measured/partial/unavailable coverage.
- Codex dashboard branding and notices distinguishing legacy and incomplete
  attribution.
- Optional remote usage-event synchronization with independent retries and an
  [additive Supabase migration](docs/migrations/2026-10-08-usage-events.sql).

### Changed

- CLI and dashboard period totals attribute measured usage to its actual local
  day. Existing collectors retain legacy session-date reporting.
- Reasoning tokens display as included in output rather than an extra additive
  category.
- Per-response events supersede cumulative snapshots. Ambiguous parent
  snapshots remain in the audit ledger but are excluded from accepted totals.
- Event dates and UTC offsets remain stable on reimport; event corrections
  invalidate acknowledgments and retry independently for each remote store.
- Enabling remote event synchronization backfills coverage metadata for
  sessions previously synchronized through the session-only interface.

### Fixed

- Reporting test fixtures tied to an expired calendar month.
- Custom-range dashboard queries binding extra filter parameters.
- Existing databases failing daily report/dashboard queries before collection
  initialized the additive schema.
- Late child discovery leaving an older parent aggregate counted outside the
  collection lookback window.
- Incomplete UTF-8 rollout tails aborting updates for unrelated sessions.
- Coverage changes committed during an in-flight remote push being incorrectly
  acknowledged as synchronized.

### Upgrade notes

- Local SQLite upgrades run automatically. Remote event sync is opt-in and
  requires applying the supplied migration and configuring `usage_table`.
- Remote event consumers must mirror local response precedence and ambiguous
  parent exclusions; summing all raw audit events can double-count usage.
- No release version has been changed and no live remote migration has been
  applied. CI rebuilds the committed dashboard assets from frontend source.

See the [design history](docs/DESIGN-HISTORY.md) for accounting decisions and
links to the approved design and implementation plan.
