# Codex session collection and daily usage attribution

## Goal and agreed behavior

Add Codex alongside Claude and Copilot. Keep a session's identity across multiple days and assign each recorded model response's tokens to the local calendar day of its usage timestamp. Resuming or clearing context does not erase previously consumed tokens. A new session ID creates a new session. Preserve raw model names and use the existing normalization function for reporting.

Example: one session consumes 50,000 tokens on October 8 and 30,000 on October 9. Its lifetime total is 80,000; the two daily totals are 50,000 and 30,000. An idle open session contributes nothing.

## Scope

Deliver Codex collection, an additive timestamped usage ledger, daily reporting, and retryable remote synchronization together. Existing Claude and Copilot collectors retain their session-level interface and historical behavior. Converting those collectors to timestamped events is a separate follow-up; do not infer daily usage from shutdown totals.

## Required implementation order

Always follow the writing-plans skill's usual test-first sequence: write a failing test, run it to verify the expected failure, implement the smallest change, run focused tests to verify they pass, and commit code and tests together. Create and update Codex tests in their owning implementation tasks. The final task verifies end-to-end integration and scenario coverage, then updates `CLAUDE.md` and `README.md` to document the verified implementation. Tests must cover every supported Codex collection scenario and the unsupported/ambiguous variants' explicit diagnostic behavior. The plan's final task contains the required scenario matrix. This replaces the earlier runtime-first, tests-at-the-end order.

## Verified repository and local-source observations

- `SessionRecord.key` and both local and remote session keys are `(session_id, source, model)`.
- Dashboard totals currently sum input, output, cache read, and cache creation. Reasoning is displayed separately.
- `ModelNormalizeMiddleware` fills `canonical_model` while retaining raw `model`. User aliases replace the bundled alias file when present.
- Local Codex JSONL files contain `session_meta`, `turn_context`, `response_item`, and `event_msg` entries. Current files also contain `token_usage_record` with response ID and per-response, turn, and thread usage.
- Current logs expose `input_tokens`, `cached_input_tokens`, `cache_write_input_tokens`, `output_tokens`, and `reasoning_output_tokens`. `event_msg` token-count entries repeat cumulative counters alongside last-request counters.
- The same local session files identify their source as `vscode`; collection must follow persisted data rather than assume only terminal sessions exist.
- An older local session has no usage entries. Missing usage is not evidence of zero consumption.
- Local log formats are observed implementation details, not a promised stable external API. Use synthetic fixtures to pin supported variants.

## Global constraints

- Python 3.11+; standard library only at runtime except the existing optional Supabase dependency.
- Preserve `(session_id, source, model)` as the session primary key; canonical names never form identity keys.
- New Codex source identifier: `codex_cli`; display label: `Codex`, covering locally persisted CLI and editor sessions.
- Keep session records and usage events frozen; transform them with `dataclasses.replace()`.
- Do not persist or sync prompts, tool arguments, tool output, reasoning text, or raw project paths.
- Existing session-only third-party collectors and stores must continue to work.
- Store UTC event timestamps and the collection machine's local day and UTC offset at the event instant; reimports of an existing event preserve its original day assignment.
- Historical session-only rows remain identifiable as legacy attribution; never describe their start-date allocation as measured daily usage.
- Planning creates documentation only; implementation, installation, live database writes, remote schema changes, and publishing are outside this request.

## Data model

Retain `sessions` as the lifetime summary and metadata table. Add `usage_events`, keyed by `(source, session_id, event_id)`, containing raw and canonical model names, UTC timestamp, local date and offset, turn ID, response ID when available, normalized token fields, and attribution quality. Add a session-level `usage_coverage` marker with values `measured`, `partial`, or `unavailable`. Absent markers identify existing legacy rows.

Codex session summaries are derived from accepted ledger events, so their totals agree with daily sums. `partial` records contain only known usage and surface that limitation. They do not receive fabricated residual events or a legacy full-total fallback. `unavailable` sessions retain metadata but do not contribute a zero-valued measured day.

`usage_daily` is a view aggregating events per session, raw model, and local date and joining current session project/context/canonical metadata. A `reporting_usage` view combines those rows with legacy session-only rows whose sessions have no coverage marker. No session is represented in both branches. The view exposes attribution quality for API/UI disclosure.

## Parsing and accounting

Prefer per-response `token_usage_record.payload.usage`, deduplicated by response ID. When those records exist, do not add legacy token-count snapshots. Read the associated model from turn context; unknown attribution stays `unknown`.

For old files without per-response records, compute component deltas between consecutive valid cumulative token snapshots. Ignore identical snapshots and entries with absent usage info. Attribute positive deltas to the snapshot timestamp and active model. The first counter is usable only when the log establishes the beginning of that session's accounting; inherited history or a counter reset makes the baseline uncertain. Emit known subsequent deltas as partial and issue a diagnostic. Never substitute the final cumulative total at the final timestamp.

Reject boolean, negative, fractional, or nonnumeric token counts; reject cache subsets exceeding total input or reasoning exceeding output. A malformed entry produces a warning and does not abort unrelated files. A partial trailing JSON line is retried on the next collection.

Normalized input is `input_tokens - cached_input_tokens - cache_write_input_tokens`; caches are stored separately. Output includes reasoning; never add reasoning again. Derive context peak from a single request's inclusive input plus output, matching the existing footprint convention rather than claiming to measure context capacity.

Deduplicate tool calls by call ID and count model requests consistently with existing session reports. Store user turn ID separately. Daily token reporting does not imply daily tool-call or user-turn telemetry; label lifetime activity metrics accordingly.

Use metadata ID rather than rollout filename for session identity. Scan recently modified active and archived files and parse their complete available histories; select by activity, not creation date. Do not discard earlier events from a selected multi-day session. A fresh import includes the entire selected session and documents that behavior. A larger lookback enables backfill.

## Forks, subagents, and clearing context

Before shipping, fixtures must establish whether root counters include child usage and whether forks copy parent response history. Use `payload.thread_id` ownership when present; deduplicate inherited response IDs across a fork family and retain usage under its originating session. Root/child usage must be represented exactly once. If ownership or aggregation cannot be established, retain the supported root data, mark coverage partial, and warn about unsupported descendant attribution rather than guessing.

Compaction and rollback do not reverse consumed tokens. Clearing the prompt context does not clear the ledger. A context reset that also resets usage counters must follow the explicit reset handling above.

## Reporting and sync

Dashboard summaries, trends, heatmaps, rolling totals, and project/model/source breakdowns read `reporting_usage`. Count distinct `(source, session_id)` sessions rather than rows, dates, or model partitions. Detailed session reports retain one row per session/model with period-scoped token totals and explicitly identified lifetime timestamps/activity metrics. The full database dump remains a raw session diagnostic. Cache rates use scoped token amounts.

Expose attribution quality and unavailable/partial-session counts so the dashboard can explain mixed historical data. Dates use the stored local assignment; day filters use the same local-day convention.

Add an optional event-store capability without changing the existing `SessionStore` contract. SQLite commits session summaries, coverage, and events atomically. Supabase writes events into a separately configured table with a new conflict key. Track event sync independently, clear its sync marker on corrections, and retry failures through both `collect` and `sync`. Stores lacking the capability receive session summaries and a clear notice that daily events were not synchronized.

## Acceptance criteria

1. One session with responses on two local dates produces two daily totals and one lifetime total equal to their sum.
2. Recollection, active/archive moves, duplicated notifications, and copied fork history do not inflate usage.
3. An old session resumed today is updated by normal scheduled collection.
4. Midnight, DST, and subsequent timezone changes do not move previously imported events between days.
5. Cache and reasoning subsets do not inflate totals; model switches remain separately attributed.
6. Missing or malformed usage is visible as unavailable or partial, never invented usage.
7. Existing databases, collectors, stores, project masking, reports, and scheduled commands remain usable.
8. A failed event sync retries without resending already acknowledged unchanged events.

## Sources

Local evidence: the repository modules named above and metadata/usage-only inspection of three local Codex rollouts on October 8, 2026. No conversation content is copied into fixtures.

Official alternative: [Codex app-server](https://learn.chatgpt.com/docs/app-server) documents stored thread listing and live `thread/tokenUsage/updated` notifications. App-server integration is outside this filesystem-collector implementation.
