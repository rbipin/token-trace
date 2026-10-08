import sqlite3
from dataclasses import replace
from src.models import SessionRecord
from src.usage import CollectionBatch, UsageCoverage
from src.stores.sqlite import SqliteStore
from usage_helpers import event

def test_daily_split_preserves_one_lifetime_summary(tmp_path):
    path = tmp_path / 'usage.db'
    store = SqliteStore(path)
    rec = SessionRecord('s1', 'codex_cli', model='gpt-5.3-codex',
                        date='2026-10-08', input_tokens=150)
    batch = CollectionBatch((rec,), (event(tokens=100),
        event(eid='r2', day='2026-10-09', tokens=50)),
        (UsageCoverage('codex_cli', 's1', 'measured'),))
    store.upsert_batch(batch)
    store.upsert_batch(batch)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
        assert conn.execute('SELECT date, input_tokens FROM usage_daily ORDER BY date').fetchall() == [
            ('2026-10-08', 100), ('2026-10-09', 50)]
        assert conn.execute('SELECT SUM(input_tokens) FROM reporting_usage').fetchone()[0] == 150

def test_reimport_preserves_original_local_date(tmp_path):
    store = SqliteStore(tmp_path / 'usage.db')
    rec = SessionRecord('s1', 'codex_cli', model='gpt-5.3-codex', date='2026-10-08')
    original = event()
    store.upsert_batch(CollectionBatch((rec,), (original,)))
    moved = replace(original, date='2026-10-09', utc_offset_minutes=540)
    store.upsert_batch(CollectionBatch((rec,), (moved,)))
    assert store.unsynced_events_for('remote')[0].date == '2026-10-08'

import pytest
from src.stores.sqlite import _CREATE_SESSIONS, _CREATE_SYNC_LOG


def test_migration_preserves_existing_sessions_and_acknowledgments(tmp_path):
    path=tmp_path/'usage.db'
    with sqlite3.connect(path) as conn:
        conn.execute(_CREATE_SESSIONS)
        conn.execute(_CREATE_SYNC_LOG)
        conn.execute("INSERT INTO sessions(session_id,source,model,date,input_tokens) VALUES ('legacy','claude_cli','m','2026-10-08',20)")
        conn.execute("INSERT INTO sync_log VALUES ('legacy','claude_cli','m','remote','2026-10-08')")
    store=SqliteStore(path)
    SqliteStore(path)
    assert store.unsynced_for('remote') == []
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT input_tokens,attribution FROM reporting_usage').fetchall() == [(20,'legacy')]


@pytest.mark.parametrize('status',['partial','unavailable'])
def test_coverage_excludes_legacy_even_without_events(tmp_path,status):
    path=tmp_path/'usage.db'
    store=SqliteStore(path)
    rec=SessionRecord('s1','codex_cli',model='m',date='2026-10-08',input_tokens=999)
    store.upsert_batch(CollectionBatch((rec,),(),(UsageCoverage('codex_cli','s1',status),)))
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM reporting_usage').fetchone()[0] == 0


def test_event_correction_clears_only_changed_event_ack(tmp_path):
    store=SqliteStore(tmp_path/'usage.db')
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08')
    original=event()
    second=event(eid='r2',tokens=50)
    store.upsert_batch(CollectionBatch((rec,),(original,second)))
    store.mark_events_synced([original,second],'remote')
    store.mark_events_synced([original,second],'other')
    store.upsert_batch(CollectionBatch((rec,),(replace(original,date='2026-10-09',utc_offset_minutes=540),second)))
    assert store.unsynced_events_for('remote') == []
    corrected=replace(original,input_tokens=120)
    store.upsert_batch(CollectionBatch((rec,),(corrected,)))
    assert [(e.event_id,e.input_tokens) for e in store.unsynced_events_for('remote')] == [('r1',120)]
    assert len(store.unsynced_events_for('other')) == 1
    assert store.unsynced_for('remote')[0].input_tokens == 170


def test_invalid_event_rolls_back_sessions_events_and_coverage(tmp_path):
    path=tmp_path/'usage.db'
    store=SqliteStore(path)
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08')
    with pytest.raises((ValueError,sqlite3.IntegrityError)):
        store.upsert_batch(CollectionBatch((rec,),(event(),replace(event(eid='bad'),input_tokens=-1)),
            (UsageCoverage('codex_cli','s1','measured'),)))
    with sqlite3.connect(path) as conn:
        for table in ('sessions','usage_events','usage_coverage'):
            assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0


def test_partial_reimport_keeps_previously_measured_consumption(tmp_path):
    store=SqliteStore(tmp_path/'usage.db')
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08',input_tokens=150)
    store.upsert_batch(CollectionBatch((rec,),(event(),event(eid='r2',tokens=50))))
    store.upsert_batch(CollectionBatch((replace(rec,input_tokens=100),),(event(),),
        (UsageCoverage('codex_cli','s1','partial','truncated history'),)))
    assert store.unsynced_for('remote')[0].input_tokens == 150


def test_coverage_correction_invalidates_session_ack(tmp_path):
    store=SqliteStore(tmp_path/'usage.db')
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08')
    batch=CollectionBatch((rec,),(),(UsageCoverage('codex_cli','s1','unavailable'),))
    store.upsert_batch(batch)
    store.mark_synced([rec],'remote')
    store.upsert_batch(batch)
    assert store.unsynced_for('remote') == []
    store.upsert_batch(replace(batch,coverage=(UsageCoverage('codex_cli','s1','partial','missing history'),)))
    assert len(store.unsynced_for('remote')) == 1


def test_response_records_supersede_previously_imported_snapshots(tmp_path):
    path=tmp_path/'usage.db'
    store=SqliteStore(path)
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08')
    old=replace(event(eid='snapshot:old'),attribution='snapshot_delta',response_id=None)
    store.upsert_batch(CollectionBatch((rec,),(old,)))
    store.upsert_batch(CollectionBatch((rec,),(event(eid='response:r1'),)))
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT SUM(input_tokens) FROM reporting_usage').fetchone()[0] == 100
        assert conn.execute('SELECT input_tokens FROM sessions').fetchone()[0] == 100
        assert conn.execute('SELECT COUNT(*) FROM usage_events').fetchone()[0] == 2


def test_events_without_matching_summary_roll_back_batch(tmp_path):
    store=SqliteStore(tmp_path/'usage.db')
    with pytest.raises(ValueError,match='summary'):
        store.upsert_batch(CollectionBatch(events=(event(),)))
    assert store.unsynced_events_for('remote') == []


def test_acknowledging_stale_event_does_not_hide_correction(tmp_path):
    store=SqliteStore(tmp_path/'usage.db')
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08')
    store.upsert_batch(CollectionBatch((rec,),(event(),)))
    sent=store.unsynced_events_for('remote')
    store.upsert_batch(CollectionBatch((rec,),(replace(event(),input_tokens=120),)))
    store.mark_events_synced(sent,'remote')
    assert store.unsynced_events_for('remote')[0].input_tokens == 120


def test_ambiguous_family_coverage_is_not_lost_when_child_is_outside_lookback(tmp_path):
    from src.usage import AMBIGUOUS_DESCENDANT_USAGE
    path=tmp_path/'usage.db'
    store=SqliteStore(path)
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08')
    snap=replace(event(eid='snapshot:old'),attribution='snapshot_delta',response_id=None)
    store.upsert_batch(CollectionBatch((rec,),(snap,),(UsageCoverage('codex_cli','s1','partial',AMBIGUOUS_DESCENDANT_USAGE),)))
    store.upsert_batch(CollectionBatch((rec,),(snap,),(UsageCoverage('codex_cli','s1','measured'),)))
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT status FROM usage_coverage').fetchone()[0] == 'partial'
        assert conn.execute('SELECT COUNT(*) FROM reporting_usage').fetchone()[0] == 0
