-- Apply manually before enabling stores.supabase.usage_table.
-- Default table names below; adapt both names when using custom configured tables.
-- Existing token_sessions rows and conflict key remain unchanged.
BEGIN;
ALTER TABLE token_sessions ADD COLUMN IF NOT EXISTS canonical_model text;
ALTER TABLE token_sessions ADD COLUMN IF NOT EXISTS usage_coverage text DEFAULT 'legacy'
    CHECK (usage_coverage IN ('legacy','measured','partial','unavailable'));
ALTER TABLE token_sessions ADD COLUMN IF NOT EXISTS usage_coverage_reason text;

CREATE TABLE IF NOT EXISTS token_usage_events (
    source text NOT NULL,
    session_id text NOT NULL,
    event_id text NOT NULL,
    model text NOT NULL,
    timestamp timestamptz NOT NULL,
    date date NOT NULL,
    utc_offset_minutes integer NOT NULL,
    input_tokens bigint NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens bigint NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    cache_read_tokens bigint NOT NULL DEFAULT 0 CHECK (cache_read_tokens >= 0),
    cache_creation_tokens bigint NOT NULL DEFAULT 0 CHECK (cache_creation_tokens >= 0),
    reasoning_tokens bigint NOT NULL DEFAULT 0 CHECK (reasoning_tokens >= 0 AND reasoning_tokens <= output_tokens),
    turn_id text,
    response_id text,
    canonical_model text,
    context text NOT NULL DEFAULT 'personal',
    attribution text NOT NULL CHECK (attribution IN ('response','snapshot_delta')),
    PRIMARY KEY (source,session_id,event_id)
);
CREATE INDEX IF NOT EXISTS token_usage_events_date ON token_usage_events(date);
CREATE INDEX IF NOT EXISTS token_usage_events_session ON token_usage_events(source,session_id,model);
-- TokenTracer's documented service-role credential bypasses RLS.
-- No public read/write policies are created; provision other access explicitly if needed.
ALTER TABLE token_usage_events ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON token_usage_events TO service_role;
COMMIT;
