"""SQLite-backed session store with sync log."""
from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from ..models import SessionRecord
from . import SessionStore

_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id             TEXT NOT NULL,
    source                 TEXT NOT NULL,
    model                  TEXT NOT NULL,
    canonical_model        TEXT,
    date                   TEXT NOT NULL,
    start_ts               TEXT,
    end_ts                 TEXT,
    project                TEXT,
    turns                  INTEGER DEFAULT 0,
    tool_calls             INTEGER DEFAULT 0,
    input_tokens           INTEGER DEFAULT 0,
    output_tokens           INTEGER DEFAULT 0,
    cache_creation_tokens  INTEGER DEFAULT 0,
    cache_read_tokens      INTEGER DEFAULT 0,
    context_peak_tokens    INTEGER DEFAULT 0,
    reasoning_tokens       INTEGER DEFAULT 0,
    context                TEXT DEFAULT 'personal',
    PRIMARY KEY (session_id, source, model, date)
)
"""

_CREATE_SYNC_LOG = """
CREATE TABLE IF NOT EXISTS sync_log (
    session_id  TEXT NOT NULL,
    source      TEXT NOT NULL,
    model       TEXT NOT NULL,
    date        TEXT NOT NULL,
    store_name  TEXT NOT NULL,
    synced_at   TEXT NOT NULL,
    PRIMARY KEY (session_id, source, model, date, store_name)
)
"""

_CREATE_RUN_LOG = """
CREATE TABLE IF NOT EXISTS run_log (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    ran_at  TEXT NOT NULL
)
"""

_SESSION_COLUMNS = (
    "session_id", "source", "model", "canonical_model", "date", "start_ts", "end_ts",
    "project", "turns", "tool_calls", "input_tokens", "output_tokens",
    "cache_creation_tokens", "cache_read_tokens", "context_peak_tokens",
    "reasoning_tokens", "context",
)

_INSERT = (
    f"INSERT INTO sessions ({', '.join(_SESSION_COLUMNS)}) "
    f"VALUES ({', '.join('?' * len(_SESSION_COLUMNS))})"
)


class SqliteStore:
    """SQLite-backed session store implementing SessionStore protocol."""

    name = "sqlite"

    def __init__(self, db_path: Path | str) -> None:
        """Initialize the SQLite store and create schema if needed.

        Args:
            db_path: Path to the SQLite database file (Path or str).
        """
        self._db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        """Create a connection to the database, creating parent directories as needed."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _migrate(self) -> None:
        """Run database migrations: create tables and drop old schema if needed."""
        with closing(self._connect()) as conn, conn:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            # Drop old schema if it exists
            if "usage" in tables and "sessions" not in tables:
                print(
                    "Warning: dropping old 'usage' table. "
                    "Re-run: python3 tracker.py collect --lookback 90",
                    file=sys.stderr,
                )
                conn.execute("DROP TABLE usage")
            # Create new schema
            conn.execute(_CREATE_SESSIONS)
            conn.execute(_CREATE_SYNC_LOG)
            conn.execute(_CREATE_RUN_LOG)
            # Add context column to pre-existing sessions tables
            cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
            if "context" not in cols:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN context TEXT DEFAULT 'personal'"
                )
            if "canonical_model" not in cols:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN canonical_model TEXT"
                )
            # Remove the retired per-event usage ledger (superseded by daily session rows)
            conn.execute("DROP VIEW IF EXISTS reporting_usage")
            conn.execute("DROP VIEW IF EXISTS usage_daily")
            for table in ("usage_events", "usage_coverage",
                          "usage_event_sync_log", "usage_coverage_sync_log"):
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            self._migrate_daily_key(conn)
            conn.commit()

    @staticmethod
    def _migrate_daily_key(conn: sqlite3.Connection) -> None:
        """Rebuild pre-daily tables so `date` is part of the primary key.

        Existing rows keep their data and date. Sync entries whose session row
        no longer exists are dropped.
        """
        session_pk = {r[1]: r[5] for r in conn.execute("PRAGMA table_info(sessions)")}
        log_cols = {r[1] for r in conn.execute("PRAGMA table_info(sync_log)")}
        if session_pk.get("date") and "date" in log_cols:
            return
        conn.commit()  # DDL above ran in autocommit; start one explicit transaction
        conn.execute("BEGIN")
        if not session_pk.get("date"):
            cols = ", ".join(_SESSION_COLUMNS)
            conn.execute("ALTER TABLE sessions RENAME TO sessions_pre_daily")
            conn.execute(_CREATE_SESSIONS)
            conn.execute(f"INSERT INTO sessions ({cols}) SELECT {cols} FROM sessions_pre_daily")
            conn.execute("DROP TABLE sessions_pre_daily")
        if "date" not in log_cols:
            conn.execute("ALTER TABLE sync_log RENAME TO sync_log_pre_daily")
            conn.execute(_CREATE_SYNC_LOG)
            conn.execute("""
                INSERT OR IGNORE INTO sync_log (session_id, source, model, date, store_name, synced_at)
                SELECT l.session_id, l.source, l.model, s.date, l.store_name, l.synced_at
                FROM sync_log_pre_daily l
                JOIN sessions s
                  ON s.session_id = l.session_id AND s.source = l.source AND s.model = l.model
            """)
            conn.execute("DROP TABLE sync_log_pre_daily")
        conn.commit()

    def upsert(self, records: list[SessionRecord]) -> int:
        """Replace each collected session's day rows.

        Records are grouped by (session_id, source). When a session's stored
        rows differ from the new set (a day added, removed, or changed), all of
        its rows are replaced and its sync_log entries cleared, so
        unsynced_for() re-pushes the whole session. Unchanged sessions are not
        touched.

        Args:
            records: List of SessionRecord objects to store.

        Returns:
            Count of records received.
        """
        if not records:
            return 0
        sessions: dict[tuple[str, str], dict[tuple, tuple]] = {}
        for r in records:
            sessions.setdefault((r.session_id, r.source), {})[r.key] = tuple(
                getattr(r, c) for c in _SESSION_COLUMNS)
        cols = ", ".join(_SESSION_COLUMNS)
        with closing(self._connect()) as conn, conn:
            for (session_id, source), rows in sessions.items():
                stored = {tuple(row) for row in conn.execute(
                    f"SELECT {cols} FROM sessions WHERE session_id = ? AND source = ?",
                    (session_id, source))}
                if stored == set(rows.values()):
                    continue
                conn.execute("DELETE FROM sync_log WHERE session_id = ? AND source = ?",
                             (session_id, source))
                conn.execute("DELETE FROM sessions WHERE session_id = ? AND source = ?",
                             (session_id, source))
                conn.executemany(_INSERT, rows.values())
        return len(records)

    def close(self) -> None:
        """Flush buffers and release resources."""
        # SQLite connections are managed via context manager,
        # so there's nothing to do here, but we implement the protocol.
        pass

    def unsynced_for(self, store_name: str) -> list[SessionRecord]:
        """Return all records not yet synced to the given store."""
        _UNSYNCED = """
        SELECT s.session_id, s.source, s.model, s.canonical_model, s.date,
               s.start_ts, s.end_ts, s.project, s.turns, s.tool_calls,
               s.input_tokens, s.output_tokens,
               s.cache_creation_tokens, s.cache_read_tokens,
               s.context_peak_tokens, s.reasoning_tokens, s.context
        FROM sessions s
        WHERE EXISTS (
            SELECT 1 FROM sessions u
            LEFT JOIN sync_log l
                ON u.session_id = l.session_id
                AND u.source = l.source
                AND u.model = l.model
                AND u.date = l.date
                AND l.store_name = ?
            WHERE u.session_id = s.session_id AND u.source = s.source
              AND l.session_id IS NULL
        )
        """
        with closing(self._connect()) as conn:
            rows = conn.execute(_UNSYNCED, (store_name,)).fetchall()
        return [
            SessionRecord(
                session_id=row[0], source=row[1], model=row[2], canonical_model=row[3],
                date=row[4], start_ts=row[5], end_ts=row[6], project=row[7],
                turns=row[8], tool_calls=row[9], input_tokens=row[10],
                output_tokens=row[11], cache_creation_tokens=row[12],
                cache_read_tokens=row[13], context_peak_tokens=row[14],
                reasoning_tokens=row[15],
                context=row[16] if row[16] is not None else "personal",
            )
            for row in rows
        ]

    def record_run(self, timestamp: str | None = None) -> None:
        """Record that `collect` executed, upserting the single run_log row."""
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO run_log (id, ran_at) VALUES (1, COALESCE(?, datetime('now')))
                ON CONFLICT(id) DO UPDATE SET ran_at = excluded.ran_at
                """,
                (timestamp,),
            )

    def mark_synced(self, records: list[SessionRecord], store_name: str) -> None:
        """Record that the given records were successfully pushed to store_name."""
        if not records:
            return
        _MARK_SYNCED = """
        INSERT OR IGNORE INTO sync_log (session_id, source, model, date, store_name, synced_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """
        with closing(self._connect()) as conn, conn:
            conn.executemany(
                _MARK_SYNCED,
                [(r.session_id, r.source, r.model, r.date, store_name) for r in records],
            )
