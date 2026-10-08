"""Tests for the fluent TrackerPipeline."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from src.models import SessionRecord
from src.pipeline import TrackerPipeline
from src.report import UsageReporter
from src.stores.sqlite import SqliteStore


class _StubCollector:
    def __init__(self, source, records, boom=False):
        self.source = source
        self._records = records
        self._boom = boom

    def collect(self, since: date):
        if self._boom:
            raise RuntimeError("kaboom")
        return self._records


def test_pipeline_merges_and_writes(tmp_db):
    rec = SessionRecord(session_id="s1", source="claude_cli", model="claude-sonnet-4-6",
                        date="2026-06-15", turns=3, input_tokens=100)
    # Same session yielded by two collectors — last writer wins → 1 row
    c1 = _StubCollector("claude_cli", [rec])
    c2 = _StubCollector("claude_cli", [rec])
    result = (
        TrackerPipeline().add(c1).add(c2)
        .since(date(2026, 1, 1)).store(SqliteStore(tmp_db)).run()
    )
    assert result.records_written == 1
    output = UsageReporter(tmp_db).report(period="day")
    assert isinstance(output, str)


def test_pipeline_isolates_failing_collector(tmp_db):
    rec = SessionRecord(session_id="s1", source="claude_cli", model="claude-sonnet-4-6",
                        date="2026-06-15", turns=1, input_tokens=50)
    good = _StubCollector("claude_cli", [rec])
    bad = _StubCollector("claude_cli", [], boom=True)
    result = TrackerPipeline().add(bad).add(good).since(date(2026, 1, 1)).store(SqliteStore(tmp_db)).run()
    assert result.records_written == 1
    assert any("claude_cli" in e for e in result.errors)


def test_pipeline_requires_since_and_store(tmp_db):
    with pytest.raises(ValueError):
        TrackerPipeline().store(SqliteStore(tmp_db)).run()
    with pytest.raises(ValueError):
        TrackerPipeline().since(date(2026, 1, 1)).run()


class _StubMiddleware:
    def __init__(self, name, fn):
        self.name = name
        self._fn = fn

    def applies(self, records):
        return True

    def process(self, records):
        return [self._fn(r) for r in records]


class _BoomMiddleware:
    name = "boom"

    def applies(self, records):
        return True

    def process(self, records):
        raise RuntimeError("middleware exploded")


def test_pipeline_runs_middleware_before_store(tmp_db):
    rec = SessionRecord(session_id="s1", source="claude_cli", model="claude-sonnet-4-6",
                        date="2026-06-15", turns=1, input_tokens=10)
    collector = _StubCollector("claude_cli", [rec])
    mw = _StubMiddleware("tag", lambda r: replace(r, canonical_model="TAGGED"))
    (
        TrackerPipeline().add(collector).since(date(2026, 1, 1))
        .middlewares(mw).stores(SqliteStore(tmp_db)).run()
    )
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT canonical_model FROM sessions WHERE session_id='s1'").fetchone()
    assert row[0] == "TAGGED"


def test_pipeline_skips_middleware_when_applies_false(tmp_db):
    rec = SessionRecord(session_id="s1", source="claude_cli", model="claude-sonnet-4-6",
                        date="2026-06-15", turns=1, input_tokens=10)
    collector = _StubCollector("claude_cli", [rec])
    mw = _StubMiddleware("tag", lambda r: replace(r, canonical_model="TAGGED"))
    mw.applies = lambda records: False
    (
        TrackerPipeline().add(collector).since(date(2026, 1, 1))
        .middlewares(mw).stores(SqliteStore(tmp_db)).run()
    )
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT canonical_model FROM sessions WHERE session_id='s1'").fetchone()
    assert row[0] is None


def test_pipeline_middleware_failure_aborts_run(tmp_db):
    rec = SessionRecord(session_id="s1", source="claude_cli", model="claude-sonnet-4-6",
                        date="2026-06-15", turns=1)
    collector = _StubCollector("claude_cli", [rec])
    with pytest.raises(RuntimeError, match="middleware exploded"):
        (
            TrackerPipeline().add(collector).since(date(2026, 1, 1))
            .middlewares(_BoomMiddleware()).stores(SqliteStore(tmp_db)).run()
        )


from datetime import date
from src.models import SessionRecord
from src.usage import CollectionBatch, UsageCoverage
from src.pipeline import TrackerPipeline
from src.stores.sqlite import SqliteStore
from usage_helpers import event

def test_batch_and_legacy_collectors_share_pipeline(tmp_path):
    class Legacy:
        source = 'claude_cli'
        def collect(self, since):
            return [SessionRecord('legacy','claude_cli', date='2026-10-08', input_tokens=20)]
    class Codex:
        source = 'codex_cli'
        def collect_batch(self, since):
            rec = SessionRecord('s1','codex_cli', model='gpt-5.3-codex',
                                date='2026-10-08', input_tokens=100)
            return CollectionBatch((rec,), (event(),),
                (UsageCoverage('codex_cli','s1','measured'),))
    store = SqliteStore(tmp_path / 'usage.db')
    result = TrackerPipeline().add(Legacy()).add(Codex()).since(date(2026,10,8)).stores(store).run()
    assert result.records_written == 2
    assert len(store.unsynced_events_for('remote')) == 1


def test_batch_events_receive_context_and_normalization(tmp_path):
    from src.middleware.model_normalize import ModelNormalizeMiddleware
    from dataclasses import replace
    class Codex:
        source='codex_cli'
        def collect_batch(self,since):
            rec=SessionRecord('s1','codex_cli',model='test-model-20261008',date='2026-10-08')
            return CollectionBatch((rec,),(replace(event(),model=rec.model),),
                (UsageCoverage('codex_cli','s1','measured'),),('synthetic diagnostic',))
    store=SqliteStore(tmp_path/'usage.db')
    result=TrackerPipeline().add(Codex()).context('work').middlewares(ModelNormalizeMiddleware()).since(date(2026,10,8)).stores(store).run()
    e=store.unsynced_events_for('remote')[0]
    assert e.context == 'work'
    assert e.canonical_model == 'test-model'
    assert e.model == 'test-model-20261008'
    assert result.events_written == 1
    assert 'synthetic diagnostic' in result.errors


def test_legacy_primary_receives_summary_and_capability_warning():
    class Codex:
        source='codex_cli'
        def collect_batch(self,since):
            return CollectionBatch((SessionRecord('s1','codex_cli',date='2026-10-08'),),(event(),))
    class LegacyStore:
        name='custom'
        def upsert(self,records):
            return len(records)
        def close(self):pass
    result=TrackerPipeline().add(Codex()).since(date(2026,10,8)).stores(LegacyStore()).run()
    assert result.records_written == 1
    assert result.events_written == 0
    assert any('event' in e and 'custom' in e for e in result.errors)


def test_run_result_existing_positional_arguments_keep_their_meaning():
    from src.pipeline import RunResult
    result=RunResult(1,2,['collector failed'],['remote failed'])
    assert result.errors == ['collector failed']
    assert result.stores_failed == ['remote failed']
    assert result.events_written == 0
