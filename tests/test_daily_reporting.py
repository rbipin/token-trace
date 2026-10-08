import sqlite3
from src.dashboard import queries
from src.models import SessionRecord
from src.stores.sqlite import SqliteStore
from src.usage import CollectionBatch, UsageCoverage
from usage_helpers import event

def test_period_totals_do_not_repeat_session_lifetime(tmp_path):
    path = tmp_path / 'usage.db'
    store = SqliteStore(path)
    rec = SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08',input_tokens=150)
    store.upsert_batch(CollectionBatch((rec,), (event(tokens=100),
        event(eid='r2',day='2026-10-09',tokens=50)),
        (UsageCoverage('codex_cli','s1','measured'),)))
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        first = queries.summary(conn,'custom','2026-10-08','2026-10-08')
        second = queries.summary(conn,'custom','2026-10-09','2026-10-09')
        both = queries.summary(conn,'all')
    assert (first['total_tokens'],second['total_tokens'],both['total_tokens']) == (100,50,150)
    assert both['session_count'] == 1

from dataclasses import replace
from datetime import date, timedelta
from src.report import UsageReporter
import json
import pytest


def seed_daily(path,day=None):
    day=day or date.today().isoformat()
    prior=(date.fromisoformat(day)-timedelta(days=1)).isoformat()
    store=SqliteStore(path)
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date=prior,project='project',start_ts=prior+'T12:00:00+00:00',tool_calls=7)
    events=(replace(event(day=prior,tokens=100),output_tokens=20,reasoning_tokens=10),
            replace(event(eid='r2',day=day,tokens=50),cache_read_tokens=150,output_tokens=10,reasoning_tokens=5))
    store.upsert_batch(CollectionBatch((rec,),events,(UsageCoverage('codex_cli','s1','measured'),)))
    return store


def test_distinct_session_counts_across_models_days_and_sources(tmp_path):
    path=tmp_path/'usage.db'
    store=seed_daily(path)
    other=SessionRecord('s1','codex_cli',model='other',date=date.today().isoformat())
    store.upsert_batch(CollectionBatch((other,),(event(eid='r3',day=date.today().isoformat(),model='other',tokens=25),)))
    store.upsert([SessionRecord('s1','claude_cli',date=date.today().isoformat(),input_tokens=20)])
    with sqlite3.connect(path) as conn:
        conn.row_factory=sqlite3.Row
        summary=queries.summary(conn,'all')
    assert summary['session_count'] == 2
    assert summary['total_tokens'] == 375


def test_attribution_discloses_mixed_and_missing_usage(tmp_path):
    path=tmp_path/'usage.db'
    store=seed_daily(path)
    store.upsert([SessionRecord('legacy','claude_cli',date=date.today().isoformat(),input_tokens=20)])
    for sid,status in [('partial','partial'),('missing','unavailable')]:
        rec=SessionRecord(sid,'codex_cli',date=date.today().isoformat(),input_tokens=999)
        store.upsert_batch(CollectionBatch((rec,),(),(UsageCoverage('codex_cli',sid,status),)))
    with sqlite3.connect(path) as conn:
        conn.row_factory=sqlite3.Row
        summary=queries.summary(conn,'all')
    assert summary['total_tokens'] == 350
    assert summary['attribution'] == dict(legacy_tokens=20,partial_session_count=1,unavailable_session_count=1)
    text=UsageReporter(path).report(period='all')
    assert 'session start' in text.lower()
    assert 'unavailable' in text.lower()


def test_custom_range_does_not_leak_bounds_into_rolling_filters(tmp_path):
    path=tmp_path/'usage.db'
    seed_daily(path)
    with sqlite3.connect(path) as conn:
        conn.row_factory=sqlite3.Row
        summary=queries.summary(conn,'custom','2020-01-01','2020-01-02',source='codex_cli')
    assert summary['total_tokens'] == 0
    assert summary['rolling']['7d']['total_tokens'] == 330


def test_all_dashboard_surfaces_share_daily_attribution(tmp_path):
    path=tmp_path/'usage.db'
    seed_daily(path)
    day=date.today().isoformat()
    prior=(date.today()-timedelta(days=1)).isoformat()
    with sqlite3.connect(path) as conn:
        conn.row_factory=sqlite3.Row
        assert queries.heatmap(conn) == [dict(date=prior,tokens=120),dict(date=day,tokens=210)]
        assert queries.trend(conn) == [dict(date=prior,source='codex_cli',tokens=120),dict(date=day,source='codex_cli',tokens=210)]
        assert queries.projects(conn,'custom',day,day) == [dict(project='project',tokens=210)]
        assert queries.project_detail(conn,'project','custom',day,day)['total_tokens'] == 210


@pytest.mark.parametrize('summary',[False,True])
def test_cli_day_scopes_tokens_and_cache_rates(tmp_path,summary):
    path=tmp_path/'usage.db'
    seed_daily(path)
    payload=json.loads(UsageReporter(path).report(period='day',summary=summary,as_json=True))
    assert payload['cache_efficiency']['hit_rate'] == .75
    row=payload['rows'][0]
    if not summary:
        assert row['input_tokens'] == 50
        assert row['output_tokens'] == 10
        assert row['tool_calls'] == 7
        assert row['activity_scope'] == 'lifetime'
    else:
        assert row['total_tokens'] == 210


def test_cli_all_groups_daily_rows_back_into_one_session_model(tmp_path):
    path=tmp_path/'usage.db'
    seed_daily(path)
    payload=json.loads(UsageReporter(path).report(period='all',as_json=True))
    assert len(payload['rows']) == 1
    assert payload['rows'][0]['input_tokens'] == 150
    assert payload['rows'][0]['tool_calls'] == 7
    text=UsageReporter(path).report(period='all')
    assert 'Lifetime' in text


def test_report_initializes_additive_schema_for_pre_feature_database(tmp_path):
    from src.stores.sqlite import _CREATE_SESSIONS, _CREATE_SYNC_LOG
    path=tmp_path/'usage.db'
    with sqlite3.connect(path) as conn:
        conn.execute(_CREATE_SESSIONS)
        conn.execute(_CREATE_SYNC_LOG)
        conn.execute("INSERT INTO sessions(session_id,source,model,date,input_tokens) VALUES ('s1','claude_cli','m','2020-01-01',20)")
    payload=json.loads(UsageReporter(path).report(period='all',as_json=True))
    assert payload['rows'][0]['input_tokens'] == 20
    assert payload['attribution']['legacy_tokens'] == 20
