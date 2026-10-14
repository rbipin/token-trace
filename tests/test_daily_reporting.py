import json
import sqlite3

from src.dashboard import queries
from src.models import SessionRecord
from src.report import UsageReporter
from src.stores.sqlite import SqliteStore


def _rec(sid, day, model='gpt-5.3-codex', source='codex_cli', **kw):
    return SessionRecord(sid, source, model=model, date=day, **kw)


def _summary(path, *args):
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return queries.summary(conn, *args)


def test_dashboard_scopes_tokens_by_row_date(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', input_tokens=100),
                              _rec('s2', '2026-10-09', input_tokens=50)])
    assert _summary(path, 'custom', '2026-10-08', '2026-10-08')['total_tokens'] == 100
    assert _summary(path, 'all')['total_tokens'] == 150


def test_session_count_is_distinct_source_and_session(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', model='a'),
                              _rec('s1', '2026-10-08', model='b'),
                              _rec('s1', '2026-10-08', source='claude_cli')])
    assert _summary(path, 'all')['session_count'] == 2


def test_summary_has_no_attribution_block(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', input_tokens=1)])
    assert 'attribution' not in _summary(path, 'all')


def test_cli_report_has_no_lifetime_labels_or_notices(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([_rec('s1', '2026-10-08', input_tokens=1)])
    text = UsageReporter(path).report(period='all')
    assert 'Lifetime' not in text
    assert 'session start dates' not in text
    payload = json.loads(UsageReporter(path).report(period='all', as_json=True))
    assert 'attribution' not in payload
    assert 'activity_scope' not in payload['rows'][0]


def test_report_groups_day_rows_into_one_session_row(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([
        _rec('s1', '2026-10-08', input_tokens=100, turns=2, tool_calls=1, context_peak_tokens=90,
             start_ts='2026-10-08T09:00:00', end_ts='2026-10-08T10:00:00'),
        _rec('s1', '2026-10-09', input_tokens=50, turns=1, tool_calls=3, context_peak_tokens=120,
             start_ts='2026-10-09T09:00:00', end_ts='2026-10-09T11:00:00')])
    rows = json.loads(UsageReporter(path).report(period='all', as_json=True))['rows']
    assert len(rows) == 1
    r = rows[0]
    assert (r['input_tokens'], r['turns'], r['tool_calls'], r['context_peak_tokens']) == (150, 3, 4, 120)
    assert (r['start_ts'], r['end_ts']) == ('2026-10-08T09:00:00', '2026-10-09T11:00:00')
    detailed = json.loads(UsageReporter(path).report(detailed=True, as_json=True))['rows']
    assert len(detailed) == 2
    assert _summary(path, 'custom', '2026-10-09', '2026-10-09')['total_tokens'] == 50


def test_session_view_is_stable_when_project_differs_across_days(tmp_path):
    path = tmp_path / 'usage.db'
    SqliteStore(path).upsert([
        _rec('s1', '2026-10-08', input_tokens=1, project='a'),
        _rec('s1', '2026-10-09', input_tokens=1, project='b')])
    rows = json.loads(UsageReporter(path).report(period='all', as_json=True))['rows']
    assert len(rows) == 1
    assert rows[0]['project'] == 'b'

