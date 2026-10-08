import json
import sqlite3
from pathlib import Path
import tracker
from src.config import Config, Paths
from src.dashboard import queries


def test_collect_append_archive_preserves_daily_totals(tmp_path, monkeypatch):
    cfg = Config(paths=Paths(copilot_home=tmp_path/'copilot',
        claude_projects=tmp_path/'claude', codex_home=tmp_path/'codex'),
        db_path=tmp_path/'usage.db', track_project_names='no', context='work')
    monkeypatch.setattr(Config, 'load', classmethod(lambda cls, **kw: cfg))
    monkeypatch.setenv('CODEX_HOME', str(cfg.paths.codex_home))
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    # Noon UTC stays on the same local date in this test, independent of the machine zone.
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-09-01T12:00:00Z', cwd=str(tmp_path/'project'), source='vscode')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex'))]
    def response(rid, day, tokens):
        return dict(type='token_usage_record', timestamp=f'{day}T12:00:00Z',
            payload=dict(session_id='s1', thread_id='s1', turn_id='t1',
                response_id=rid, usage=dict(input_tokens=tokens, output_tokens=0)))
    rows += [response('r1','2026-10-08',100), response('r2','2026-10-09',50)]
    path = cfg.paths.codex_home/'sessions'/'rollout.jsonl'
    path.parent.mkdir(parents=True)
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
    parser = tracker.build_parser()
    def collect():
        args = parser.parse_args(['--db',str(cfg.db_path),'collect','--lookback','1'])
        assert args.run(args) == 0
    collect()
    with sqlite3.connect(cfg.db_path) as conn:
        original = conn.execute('SELECT event_id,date,utc_offset_minutes FROM usage_events ORDER BY event_id').fetchall()
        assert len(original) == 2
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(response('r3','2026-10-10',25))+'\n')
    collect()
    archived = cfg.paths.codex_home/'archived_sessions'/'renamed.jsonl'
    archived.parent.mkdir(parents=True)
    path.rename(archived)
    collect()
    with sqlite3.connect(cfg.db_path) as conn:
        conn.row_factory = sqlite3.Row
        assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM usage_events').fetchone()[0] == 3
        current = conn.execute('SELECT event_id,date,utc_offset_minutes FROM usage_events ORDER BY event_id').fetchall()
        assert [tuple(row) for row in current[:2]] == original
        summary = queries.summary(conn,'all')
        assert (summary['total_tokens'],summary['session_count']) == (175,1)
        record = conn.execute('SELECT * FROM sessions').fetchone()
        assert record['input_tokens'] == 175
        assert record['context'] == 'work'
        assert record['canonical_model'] == 'gpt-5.3-codex'
        assert record['project'] and record['project'] != str(tmp_path/'project')
    report_args = parser.parse_args(['--db',str(cfg.db_path),'report','--period','all','--summary','--json'])
    assert report_args.run(report_args) == 0

import pytest
from test_codex_cli_collector import metadata,context,usage_row,write_rollout
from test_usage_sync import Remote
from src.stores.sqlite import SqliteStore
from src.commands.common import run_sync
from src.report import UsageReporter


@pytest.mark.parametrize('mode',['yes','no','whimsical'])
@pytest.mark.parametrize('label',['work','personal'])
def test_project_masking_context_and_remote_retry_through_collect(tmp_path,monkeypatch,mode,label):
    from src.commands import collect as command
    cfg=Config(paths=Paths(tmp_path/'copilot',tmp_path/'claude',tmp_path/'codex'),
        db_path=tmp_path/'usage.db',track_project_names=mode,context=label)
    monkeypatch.setattr(Config,'load',classmethod(lambda cls,**kw:cfg))
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    row=metadata(cwd=str(tmp_path/'project'))
    write_rollout(cfg.paths.codex_home,[row,context(),usage_row('r1','2026-10-08T12:01:00Z',100)])
    remote=Remote(fail_events=True)
    monkeypatch.setattr(command,'load_remote_stores',lambda cfg:[remote])
    parser=tracker.build_parser()
    args=parser.parse_args(['--db',str(cfg.db_path),'collect','--lookback','1'])
    assert args.run(args) == 0
    store=SqliteStore(cfg.db_path)
    assert store.unsynced_for('remote') == []
    assert len(store.unsynced_events_for('remote')) == 1
    remote.fail_events=False
    assert args.run(args) == 0
    assert len(remote.sessions) == 1
    assert len(remote.events) == 1
    assert remote.events[0].context == label
    assert str(tmp_path) not in repr(remote.events)
    assert str(tmp_path) not in repr(remote.sessions)
    project=remote.sessions[0].project
    assert project == 'project' if mode=='yes' else project != 'project'
    if mode == 'no':
        assert len(project) == 12
    payload=json.loads(UsageReporter(cfg.db_path).report(period='all',summary=True,as_json=True))
    assert sum(r['input_tokens'] for r in payload['rows']) == 100
    assert store.unsynced_events_for('remote') == []
