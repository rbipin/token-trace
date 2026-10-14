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
