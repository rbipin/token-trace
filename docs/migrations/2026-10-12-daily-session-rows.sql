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
