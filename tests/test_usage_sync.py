from src.commands.common import run_sync
from src.models import SessionRecord
from src.stores.sqlite import SqliteStore
from src.usage import CollectionBatch, UsageCoverage
from usage_helpers import event

def test_event_failure_retries_after_sessions_succeed(tmp_path):
    class Remote:
        name = 'remote'
        fail_events = True
        session_pushes = 0
        def upsert(self, records):
            self.session_pushes += len(records)
            return len(records)
        def upsert_events(self, events):
            if self.fail_events:
                raise RuntimeError('event table unavailable')
            return len(events)
        def close(self):
            pass
    store = SqliteStore(tmp_path / 'usage.db')
    rec = SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08',input_tokens=100)
    store.upsert_batch(CollectionBatch((rec,), (event(),),
        (UsageCoverage('codex_cli','s1','measured'),)))
    remote = Remote()
    run_sync(store,[remote],False)
    assert store.unsynced_for('remote') == []
    assert len(store.unsynced_events_for('remote')) == 1
    remote.fail_events = False
    run_sync(store,[remote],False)
    assert store.unsynced_events_for('remote') == []
    assert remote.session_pushes == 1

from dataclasses import replace
import pytest


class Remote:
    def __init__(self,name='remote',fail_sessions=False,fail_events=False):
        self.name=name
        self.fail_sessions=fail_sessions
        self.fail_events=fail_events
        self.sessions=[]
        self.events=[]
    def upsert(self,records):
        if self.fail_sessions: raise RuntimeError('sessions unavailable')
        self.sessions.extend(records)
        return len(records)
    def upsert_events(self,events):
        if self.fail_events: raise RuntimeError('events unavailable')
        self.events.extend(events)
        return len(events)
    def close(self): pass


def seeded(tmp_path):
    store=SqliteStore(tmp_path/'usage.db')
    rec=SessionRecord('s1','codex_cli',model='gpt-5.3-codex',date='2026-10-08',input_tokens=100)
    store.upsert_batch(CollectionBatch((rec,),(event(),),(UsageCoverage('codex_cli','s1','measured'),)))
    return store,rec


def test_failed_sessions_do_not_prevent_event_ack(tmp_path):
    store,rec=seeded(tmp_path)
    remote=Remote(fail_sessions=True)
    result=run_sync(store,[remote],False)
    assert result['remote']['failed'] is True
    assert store.unsynced_events_for('remote') == []
    assert len(store.unsynced_for('remote')) == 1
    remote.fail_sessions=False
    run_sync(store,[remote],False)
    assert store.unsynced_for('remote') == []
    assert len(remote.events) == 1


def test_corrected_event_retries_independently_per_store(tmp_path):
    store,rec=seeded(tmp_path)
    a,b=Remote('a'),Remote('b',fail_events=True)
    run_sync(store,[a,b],False)
    assert store.unsynced_events_for('a') == []
    assert len(store.unsynced_events_for('b')) == 1
    store.upsert_batch(CollectionBatch((rec,),(replace(event(),input_tokens=120),)))
    run_sync(store,[a,b],False)
    assert a.events[-1].input_tokens == 120
    b.fail_events=False
    run_sync(store,[b],False)
    assert b.events[-1].input_tokens == 120
    before=(len(a.sessions),len(a.events))
    run_sync(store,[a],False)
    assert (len(a.sessions),len(a.events)) == before


def test_session_only_store_keeps_events_pending_and_warns(tmp_path,capsys):
    store,_=seeded(tmp_path)
    class Legacy:
        name='legacy'
        def upsert(self,records): return len(records)
        def close(self): pass
    result=run_sync(store,[Legacy()],False)
    assert result['legacy']['pushed'] == 1
    assert result['legacy']['events_pending'] == 1
    assert len(store.unsynced_events_for('legacy')) == 1
    assert 'usage events' in capsys.readouterr().err


def test_dry_run_reports_events_without_clients_or_acknowledgments(tmp_path):
    from src.stores.supabase import SupabaseStore
    store,_=seeded(tmp_path)
    remote=SupabaseStore('invalid','unused',usage_table='events')
    result=run_sync(store,[remote],True)
    assert result['supabase'] == dict(pending=1,events_pending=1)
    assert remote._client_cache is None
    assert len(store.unsynced_events_for('supabase')) == 1


def test_pipeline_pushes_events_and_retry_sweep_does_not_repeat(tmp_path):
    from src.pipeline import TrackerPipeline
    from datetime import date
    store,rec=seeded(tmp_path)
    class Collector:
        source='codex_cli'
        def collect_batch(self,since): return CollectionBatch((rec,),(event(),))
    remote=Remote()
    result=TrackerPipeline().add(Collector()).since(date(2026,10,8)).stores(store,remote).run()
    assert result.stores_failed == []
    assert store.unsynced_events_for('remote') == []
    run_sync(store,[remote],False)
    assert len(remote.events) == 1


def test_sync_cli_reports_pending_events(tmp_path,monkeypatch,capsys):
    import tracker
    from src.config import Config, StoreConfig
    from src.commands import sync as sync_cmd
    store,_=seeded(tmp_path)
    cfg=Config(db_path=tmp_path/'usage.db',remote_stores=(StoreConfig('remote',None,{}),))
    monkeypatch.setattr(Config,'load',classmethod(lambda cls,**kw:cfg))
    monkeypatch.setattr(sync_cmd,'load_remote_stores',lambda cfg:[Remote()])
    args=tracker.build_parser().parse_args(['--db',str(cfg.db_path),'sync','--dry-run'])
    assert args.run(args) == 0
    assert '1 usage events pending' in capsys.readouterr().out
