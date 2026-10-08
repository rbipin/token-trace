"""Additive usage ledger schema and transaction-local persistence helpers."""
from __future__ import annotations

from dataclasses import asdict, fields, replace
import sqlite3

from ..usage import AMBIGUOUS_DESCENDANT_USAGE, CollectionBatch, UsageCoverage, UsageEvent, event_time

EVENT_COLUMNS = tuple(f.name for f in fields(UsageEvent))
TOKEN_COLUMNS = ('input_tokens', 'output_tokens', 'cache_read_tokens',
                 'cache_creation_tokens', 'reasoning_tokens')


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute('''CREATE TABLE IF NOT EXISTS usage_events (
        session_id TEXT NOT NULL, source TEXT NOT NULL, event_id TEXT NOT NULL,
        model TEXT NOT NULL, timestamp TEXT NOT NULL, date TEXT NOT NULL,
        utc_offset_minutes INTEGER NOT NULL,
        input_tokens INTEGER NOT NULL CHECK(input_tokens >= 0),
        output_tokens INTEGER NOT NULL CHECK(output_tokens >= 0),
        cache_read_tokens INTEGER NOT NULL CHECK(cache_read_tokens >= 0),
        cache_creation_tokens INTEGER NOT NULL CHECK(cache_creation_tokens >= 0),
        reasoning_tokens INTEGER NOT NULL CHECK(reasoning_tokens >= 0 AND reasoning_tokens <= output_tokens),
        turn_id TEXT, response_id TEXT, canonical_model TEXT,
        context TEXT NOT NULL DEFAULT 'personal',
        attribution TEXT NOT NULL CHECK(attribution IN ('response','snapshot_delta')),
        PRIMARY KEY(source,session_id,event_id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS usage_coverage (
        source TEXT NOT NULL, session_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('measured','partial','unavailable')),
        reason TEXT, PRIMARY KEY(source,session_id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS usage_event_sync_log (
        source TEXT NOT NULL, session_id TEXT NOT NULL, event_id TEXT NOT NULL,
        store_name TEXT NOT NULL, synced_at TEXT NOT NULL,
        PRIMARY KEY(source,session_id,event_id,store_name))''')
    conn.execute('CREATE INDEX IF NOT EXISTS usage_events_date ON usage_events(date)')
    conn.execute('CREATE INDEX IF NOT EXISTS usage_events_session ON usage_events(source,session_id,model)')
    conn.execute(f'''CREATE VIEW IF NOT EXISTS usage_daily AS
        SELECT e.session_id, e.source, e.model,
            COALESCE(s.canonical_model,e.canonical_model) AS canonical_model,
            e.date, MIN(e.timestamp) AS start_ts, MAX(e.timestamp) AS end_ts,
            s.project, COUNT(*) AS turns, 0 AS tool_calls,
            SUM(e.input_tokens) AS input_tokens, SUM(e.output_tokens) AS output_tokens,
            SUM(e.cache_creation_tokens) AS cache_creation_tokens,
            SUM(e.cache_read_tokens) AS cache_read_tokens,
            MAX(e.input_tokens+e.cache_read_tokens+e.cache_creation_tokens+e.output_tokens) AS context_peak_tokens,
            SUM(e.reasoning_tokens) AS reasoning_tokens,
            COALESCE(s.context,e.context) AS context,
            s.start_ts AS lifetime_start_ts, s.end_ts AS lifetime_end_ts,
            s.turns AS lifetime_turns, s.tool_calls AS lifetime_tool_calls,
            COALESCE(c.status,'partial') AS coverage,
            CASE WHEN COUNT(DISTINCT e.attribution)=1 THEN MIN(e.attribution) ELSE 'mixed' END AS attribution
        FROM usage_events e
        JOIN sessions s ON s.session_id=e.session_id AND s.source=e.source AND s.model=e.model
        LEFT JOIN usage_coverage c ON c.source=e.source AND c.session_id=e.session_id
        WHERE NOT (COALESCE(c.reason,'')='{AMBIGUOUS_DESCENDANT_USAGE}' AND e.attribution='snapshot_delta')
          AND NOT (e.attribution='snapshot_delta' AND EXISTS (
              SELECT 1 FROM usage_events r WHERE r.source=e.source AND r.session_id=e.session_id AND r.attribution='response'))
        GROUP BY e.source,e.session_id,e.model,e.date''')
    columns = ('session_id,source,model,canonical_model,date,start_ts,end_ts,project,turns,tool_calls,'
               'input_tokens,output_tokens,cache_creation_tokens,cache_read_tokens,context_peak_tokens,'
               'reasoning_tokens,context,lifetime_start_ts,lifetime_end_ts,lifetime_turns,'
               'lifetime_tool_calls,coverage,attribution')
    conn.execute(f'''CREATE VIEW IF NOT EXISTS reporting_usage AS
        SELECT {columns} FROM usage_daily
        UNION ALL
        SELECT s.session_id,s.source,s.model,s.canonical_model,s.date,s.start_ts,s.end_ts,s.project,
            s.turns,s.tool_calls,s.input_tokens,s.output_tokens,s.cache_creation_tokens,s.cache_read_tokens,
            s.context_peak_tokens,s.reasoning_tokens,s.context,s.start_ts,s.end_ts,s.turns,s.tool_calls,
            'legacy','legacy'
        FROM sessions s WHERE NOT EXISTS (
            SELECT 1 FROM usage_coverage c WHERE c.source=s.source AND c.session_id=s.session_id)''')


def persist(conn: sqlite3.Connection, batch: CollectionBatch) -> None:
    columns = ','.join(EVENT_COLUMNS)
    updates = ','.join(f'{c}=excluded.{c}' for c in EVENT_COLUMNS
                       if c not in ('source','session_id','event_id','date','utc_offset_minutes'))
    coverage = {(c.source,c.session_id): c for c in batch.coverage}
    affected = set(coverage)
    for event in batch.events:
        if not conn.execute('SELECT 1 FROM sessions WHERE source=? AND session_id=? AND model=?',
                            (event.source,event.session_id,event.model)).fetchone():
            raise ValueError('usage event requires a matching session summary')
        if any(type(getattr(event,c)) is not int or getattr(event,c) < 0 for c in TOKEN_COLUMNS):
            raise ValueError('usage counts must be nonnegative integers')
        if event.reasoning_tokens > event.output_tokens:
            raise ValueError('reasoning exceeds output')
        event_time(event.timestamp)
        if not all((event.session_id,event.source,event.event_id,event.model)):
            raise ValueError('usage identity must not be empty')
        existing=conn.execute(f'SELECT {columns} FROM usage_events WHERE source=? AND session_id=? AND event_id=?',event.key).fetchone()
        stored=replace(event,date=existing[5],utc_offset_minutes=existing[6]) if existing else event
        row=tuple(asdict(stored).values())
        if existing is not None and tuple(existing) != row:
            conn.execute('DELETE FROM usage_event_sync_log WHERE source=? AND session_id=? AND event_id=?',event.key)
        conn.execute(f'INSERT INTO usage_events ({columns}) VALUES ({",".join("?" for _ in EVENT_COLUMNS)}) '
                     f'ON CONFLICT(source,session_id,event_id) DO UPDATE SET {updates}',row)
        key=(event.source,event.session_id)
        affected.add(key)
        if key not in coverage and not conn.execute('SELECT 1 FROM usage_coverage WHERE source=? AND session_id=?',key).fetchone():
            coverage[key]=UsageCoverage(*key,'measured')
    for key,c in coverage.items():
        existing=conn.execute('SELECT status,reason FROM usage_coverage WHERE source=? AND session_id=?',key).fetchone()
        if existing is None or tuple(existing) != (c.status,c.reason):
            conn.execute('DELETE FROM sync_log WHERE source=? AND session_id=?',key)
        conn.execute('INSERT INTO usage_coverage(source,session_id,status,reason) VALUES (?,?,?,?) '
                     'ON CONFLICT(source,session_id) DO UPDATE SET status=excluded.status,reason=excluded.reason',
                     (*key,c.status,c.reason))
    # Recompute from the persisted ledger so a shortened/corrupt reimport cannot erase consumption.
    for key in affected:
        marker=conn.execute('SELECT reason FROM usage_coverage WHERE source=? AND session_id=?',key).fetchone()
        has_responses=conn.execute("SELECT 1 FROM usage_events WHERE source=? AND session_id=? AND attribution='response' LIMIT 1",key).fetchone()
        reject_snapshots=bool(has_responses or (marker and marker[0]==AMBIGUOUS_DESCENDANT_USAGE))
        models=conn.execute('SELECT model FROM sessions WHERE source=? AND session_id=?',key).fetchall()
        for (model,) in models:
            values=conn.execute('SELECT '+','.join(f'COALESCE(SUM({c}),0)' for c in TOKEN_COLUMNS)+
                ',COUNT(*),COALESCE(MAX(input_tokens+cache_read_tokens+cache_creation_tokens+output_tokens),0) '
                "FROM usage_events WHERE source=? AND session_id=? AND model=? AND (?=0 OR attribution!='snapshot_delta')",
                (*key,model,int(reject_snapshots))).fetchone()
            old=conn.execute('SELECT '+','.join(TOKEN_COLUMNS)+',turns,context_peak_tokens FROM sessions '
                             'WHERE source=? AND session_id=? AND model=?',(*key,model)).fetchone()
            if old is not None and tuple(old) != tuple(values):
                conn.execute('DELETE FROM sync_log WHERE source=? AND session_id=? AND model=?',(*key,model))
                conn.execute('UPDATE sessions SET '+','.join(f'{c}=?' for c in TOKEN_COLUMNS)+
                             ',turns=?,context_peak_tokens=? WHERE source=? AND session_id=? AND model=?',
                             (*values,*key,model))


def pending(conn: sqlite3.Connection, store_name: str) -> list[UsageEvent]:
    conn.row_factory=sqlite3.Row
    rows=conn.execute('SELECT '+','.join('e.'+c for c in EVENT_COLUMNS)+
        ' FROM usage_events e WHERE NOT EXISTS (SELECT 1 FROM usage_event_sync_log l '
        'WHERE l.source=e.source AND l.session_id=e.session_id AND l.event_id=e.event_id AND l.store_name=?) '
        'ORDER BY e.source,e.session_id,e.timestamp,e.event_id',(store_name,)).fetchall()
    return [UsageEvent(**dict(row)) for row in rows]


def acknowledge(conn: sqlite3.Connection, events: list[UsageEvent], store_name: str) -> None:
    for event in events:
        current=conn.execute('SELECT '+','.join(EVENT_COLUMNS)+' FROM usage_events WHERE source=? AND session_id=? AND event_id=?',event.key).fetchone()
        if current is not None and tuple(current)==tuple(asdict(event).values()):
            conn.execute("INSERT OR IGNORE INTO usage_event_sync_log VALUES (?,?,?,?,datetime('now'))",(*event.key,store_name))
