import sqlite3
from datetime import date

from src.models import SessionRecord
from src.pipeline import TrackerPipeline
from src.stores.sqlite import SqliteStore

LEDGER = {'usage_events', 'usage_coverage', 'usage_event_sync_log',
          'usage_coverage_sync_log', 'usage_daily', 'reporting_usage'}


def test_store_drops_event_ledger_objects(tmp_path):
    path = tmp_path / 'usage.db'
    with sqlite3.connect(path) as conn:
        for table in ('usage_events', 'usage_coverage', 'usage_event_sync_log', 'usage_coverage_sync_log'):
            conn.execute(f'CREATE TABLE {table} (x)')
        conn.execute('CREATE VIEW usage_daily AS SELECT x FROM usage_events')
        conn.execute('CREATE VIEW reporting_usage AS SELECT x FROM usage_daily')
    SqliteStore(path)
    with sqlite3.connect(path) as conn:
        names = {r[0] for r in conn.execute('SELECT name FROM sqlite_master')}
    assert not names & LEDGER


def test_pipeline_uses_collect_only(tmp_path):
    class Both:
        source = 'codex_cli'

        def collect(self, since):
            return [SessionRecord('s1', 'codex_cli', date='2026-10-08', input_tokens=5)]

        def collect_batch(self, since):
            raise AssertionError('ledger path removed')

    result = (TrackerPipeline().add(Both()).since(date(2026, 10, 1))
              .stores(SqliteStore(tmp_path / 'usage.db')).run())
    assert result.records_written == 1
    assert result.errors == []
