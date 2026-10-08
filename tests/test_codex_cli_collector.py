import json
from datetime import date
from zoneinfo import ZoneInfo
from src.collectors.codex_cli import CodexCliCollector

def write_rollout(root, rows, name='rollout.jsonl'):
    path = root / 'sessions' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
    return path

def usage_row(rid, ts, tokens):
    return dict(type='token_usage_record', timestamp=ts, payload=dict(
        session_id='s1', thread_id='s1', turn_id='t1', response_id=rid,
        usage=dict(input_tokens=tokens, output_tokens=0)))

def test_resumed_session_splits_usage_across_days(tmp_path):
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-09-01T12:00:00Z', cwd='/synthetic/project', source='vscode')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-09T03:59:59Z', 100),
        usage_row('r2', '2026-10-09T04:00:00Z', 50)]
    write_rollout(tmp_path, rows)
    batch = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect_batch(date(2026,10,8))
    assert [(e.date, e.input_tokens) for e in batch.events] == [('2026-10-08',100),('2026-10-09',50)]
    assert batch.sessions[0].session_id == 's1'
    assert batch.sessions[0].input_tokens == 150

def test_recent_activity_selects_old_session(tmp_path):
    import os
    from datetime import datetime, timezone
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-09-01T12:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-08T12:00:00Z', 100)]
    path = write_rollout(tmp_path, rows)
    modified = datetime(2026, 10, 8, 16, tzinfo=timezone.utc).timestamp()
    os.utime(path, (modified, modified))
    batch = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect_batch(date(2026,10,8))
    assert len(batch.sessions) == 1
    assert sum(e.input_tokens for e in batch.events) == 100


def test_partial_tail_completed_on_next_import(tmp_path):
    rows = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-10-08T12:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-08T12:01:00Z', 100)]
    path = write_rollout(tmp_path, rows)
    final = json.dumps(usage_row('r2', '2026-10-08T12:02:00Z', 50))
    with path.open('a', encoding='utf-8') as stream:
        stream.write(final[:len(final)//2])
    collector = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit'))
    before = collector.collect_batch(date(2026,10,8))
    assert [(e.response_id, e.input_tokens) for e in before.events] == [('r1',100)]
    assert before.coverage[0].status == 'partial'
    with path.open('a', encoding='utf-8') as stream:
        stream.write(final[len(final)//2:] + '\n')
    after = collector.collect_batch(date(2026,10,8))
    again = collector.collect_batch(date(2026,10,8))
    assert [(e.response_id, e.input_tokens) for e in after.events] == [('r1',100),('r2',50)]
    assert again.events == after.events


def test_fork_copied_response_retains_originating_owner(tmp_path):
    parent = [dict(type='session_meta', payload=dict(id='s1',
        timestamp='2026-10-08T12:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        usage_row('r1', '2026-10-08T12:01:00Z', 100)]
    write_rollout(tmp_path, parent, 'parent.jsonl')
    child = [dict(type='session_meta', payload=dict(id='child',
        timestamp='2026-10-08T12:02:00Z', source='cli')),
        parent[1], parent[2]]
    own = usage_row('r2', '2026-10-08T12:03:00Z', 50)
    own['payload'].update(session_id='child', thread_id='child')
    child.append(own)
    write_rollout(tmp_path, child, 'child.jsonl')
    batch = CodexCliCollector(tmp_path, tz=ZoneInfo('America/Detroit')).collect_batch(date(2026,10,8))
    assert sorted((e.session_id,e.response_id,e.input_tokens) for e in batch.events) == [
        ('child','r2',50), ('s1','r1',100)]
    assert sum(r.input_tokens for r in batch.sessions) == 150

from dataclasses import replace
from datetime import datetime, timezone
import os
import pytest


def metadata(sid='s1',**kw):
    return dict(type='session_meta',payload=dict(id=sid,timestamp='2026-10-08T12:00:00Z',source='cli',**kw))


def context(model='gpt-5.3-codex',tid='t1'):
    return dict(type='turn_context',payload=dict(turn_id=tid,model=model))


def snapshot(tokens,minute=1,**kw):
    return dict(type='event_msg',timestamp=f'2026-10-08T12:{minute:02d}:00Z',payload=dict(type='token_count',
        info=dict(total_token_usage=dict(input_tokens=tokens,output_tokens=0),**kw)))


def collect(root):
    return CodexCliCollector(root,tz=ZoneInfo('America/Detroit')).collect_batch(date(2026,10,8))


@pytest.mark.parametrize('source',['cli','vscode'])
def test_cli_and_editor_variants_use_metadata_id(tmp_path,source):
    meta=metadata()
    meta['payload']['source']=source
    write_rollout(tmp_path,[meta,context(),usage_row('r1','2026-10-08T12:01:00Z',100)],'nested/not-session-id.jsonl')
    batch=collect(tmp_path)
    assert batch.sessions[0].session_id == 's1'
    assert batch.events[0].input_tokens == 100
    assert batch.coverage[0].status == 'measured'


@pytest.mark.parametrize('rows,expected,coverage',[
    ([],0,None),([metadata(),context()],0,'unavailable'),
    ([metadata(),context(),snapshot(0),snapshot(100),snapshot(100),snapshot(150,2)],150,'measured'),
    ([metadata(),context(),snapshot(100),snapshot(150,2)],50,'partial'),
    ([metadata(),context(),snapshot(0),snapshot(100),snapshot(10,2),snapshot(30,3)],120,'partial'),
    ([metadata(),context(),snapshot(0),snapshot(100),snapshot(10,2,accounting_reset=True),snapshot(30,3)],130,'measured'),
    ([metadata(),context(),dict(type='event_msg',timestamp='2026-10-08T12:01:00Z',payload=dict(type='token_count',info=None))],0,'unavailable'),
    ([metadata(),context(),dict(type='event_msg',timestamp='2026-10-08T12:01:00Z',payload=dict(type='token_count',info=dict(last_token_usage=dict(input_tokens=100))))],0,'partial'),
])
def test_cumulative_baselines_and_unavailable_usage(tmp_path,rows,expected,coverage):
    write_rollout(tmp_path,rows)
    batch=collect(tmp_path)
    assert sum(e.input_tokens for e in batch.events) == expected
    if coverage:
        assert batch.coverage[0].status == coverage
        if coverage == 'partial':
            assert batch.diagnostics
    else:
        assert batch.coverage == ()


@pytest.mark.parametrize('missing_id',[False,True])
def test_per_response_precedes_snapshots_and_duplicates(tmp_path,missing_id):
    row=usage_row('r1','2026-10-08T12:01:00Z',100)
    if missing_id:
        row['payload'].pop('response_id')
    path=write_rollout(tmp_path,[metadata(),context(),snapshot(0),snapshot(500),row,row])
    batch=collect(tmp_path)
    assert len(batch.events) == 1
    assert batch.events[0].input_tokens == 100
    assert batch.coverage[0].status == ('partial' if missing_id else 'measured')
    archived=tmp_path/'archived_sessions'/'renamed.jsonl'
    archived.parent.mkdir()
    archived.write_bytes(path.read_bytes())
    assert collect(tmp_path).events == batch.events
    path.unlink()
    assert collect(tmp_path).events == batch.events


@pytest.mark.parametrize('value',[-1,True,1.5,'100',None])
def test_invalid_usage_is_diagnosed_without_aborting_other_entries(tmp_path,value):
    invalid=usage_row('bad','2026-10-08T12:01:00Z',value)
    write_rollout(tmp_path,[metadata(),context(),invalid,usage_row('r1','2026-10-08T12:02:00Z',100)])
    batch=collect(tmp_path)
    assert len(batch.events) == 1
    assert batch.events[0].input_tokens == 100
    assert batch.coverage[0].status == 'partial'
    assert any('usage' in d for d in batch.diagnostics)


@pytest.mark.parametrize('bad',['{invalid}\n','[]\n','42\n','null\n'])
def test_malformed_middle_and_scalar_rows_continue(tmp_path,bad):
    path=write_rollout(tmp_path,[metadata(),context()])
    with path.open('a') as stream:
        stream.write(bad+'\n'+json.dumps(usage_row('r1','2026-10-08T12:01:00Z',100))+'\n')
    batch=collect(tmp_path)
    assert len(batch.events) == 1
    assert batch.coverage[0].status == 'partial'
    assert batch.diagnostics


@pytest.mark.parametrize('rows',[[dict(type='session_meta',payload={})],
    [dict(type='session_meta',payload=dict(id='s1',timestamp='invalid'))],
    [dict(type='session_meta',payload=dict(id='s1'))]])
def test_invalid_session_metadata_never_invents_identity(tmp_path,rows):
    write_rollout(tmp_path,rows+[context(),usage_row('r1','2026-10-08T12:01:00Z',100)])
    batch=collect(tmp_path)
    assert not batch.sessions and not batch.events
    assert batch.diagnostics


def test_missing_home_and_untouched_file_are_safe(tmp_path):
    assert collect(tmp_path).sessions == ()
    path=write_rollout(tmp_path,[metadata(),context(),usage_row('r1','2026-10-08T12:01:00Z',100)])
    old=datetime(2026,9,1,12,tzinfo=timezone.utc).timestamp()
    os.utime(path,(old,old))
    assert collect(tmp_path).sessions == ()
    assert len(CodexCliCollector(tmp_path).collect_batch(date(2026,9,1)).events) == 1


def test_model_switch_and_tool_call_deduplication(tmp_path):
    row=usage_row('r2','2026-10-08T12:02:00Z',50)
    row['payload']['turn_id']='t2'
    tool=dict(type='response_item',payload=dict(type='custom_tool_call',call_id='call1'))
    write_rollout(tmp_path,[metadata(),context(),usage_row('r1','2026-10-08T12:01:00Z',100),tool,tool,
        context('different-model','t2'),row])
    batch=collect(tmp_path)
    assert [(r.model,r.input_tokens,r.turns,r.tool_calls,r.context_peak_tokens) for r in batch.sessions] == [
        ('gpt-5.3-codex',100,1,1,100),('different-model',50,1,0,50)]


@pytest.mark.parametrize('kind',['compacted','rollback','task_aborted','task_failed'])
def test_conversation_state_does_not_reverse_consumption(tmp_path,kind):
    write_rollout(tmp_path,[metadata(),context(),usage_row('r1','2026-10-08T12:01:00Z',100),
        dict(type='event_msg',payload=dict(type=kind)),usage_row('r2','2026-10-08T12:02:00Z',50)])
    assert sum(e.input_tokens for e in collect(tmp_path).events) == 150


def test_zero_usage_is_measured_not_unavailable(tmp_path):
    write_rollout(tmp_path,[metadata(),context(),usage_row('r1','2026-10-08T12:01:00Z',0)])
    batch=collect(tmp_path)
    assert len(batch.events) == 1
    assert batch.coverage[0].status == 'measured'


def test_unknown_model_stays_unknown(tmp_path):
    write_rollout(tmp_path,[metadata(),usage_row('r1','2026-10-08T12:01:00Z',100)])
    assert collect(tmp_path).events[0].model == 'unknown'


def test_ambiguous_descendant_snapshot_is_not_added_to_root(tmp_path):
    meta=metadata(source_info='subagent')
    meta['payload']['source']={'subagent':{'parent_thread_id':'parent'}}
    write_rollout(tmp_path,[meta,context(),snapshot(0),snapshot(100)])
    batch=collect(tmp_path)
    assert not batch.events
    assert batch.coverage[0].status == 'partial'
    assert batch.diagnostics


def test_invalid_snapshot_timestamp_does_not_advance_baseline(tmp_path):
    invalid=snapshot(100)
    invalid['timestamp']='invalid'
    write_rollout(tmp_path,[metadata(),context(),snapshot(0),invalid,snapshot(150,2)])
    batch=collect(tmp_path)
    assert sum(e.input_tokens for e in batch.events) == 150
    assert batch.coverage[0].status == 'partial'
    assert batch.diagnostics


def test_unreadable_file_does_not_block_other_sessions(tmp_path,monkeypatch):
    from pathlib import Path
    blocked=write_rollout(tmp_path,[metadata()],'blocked.jsonl')
    write_rollout(tmp_path,[metadata(),context(),usage_row('r1','2026-10-08T12:01:00Z',100)],'good.jsonl')
    real=Path.open
    def open_path(path,*args,**kwargs):
        if path == blocked:
            raise PermissionError('unreadable')
        return real(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',open_path)
    batch=collect(tmp_path)
    assert len(batch.events) == 1
    assert any('read' in d for d in batch.diagnostics)


def test_cumulative_file_without_metadata_is_diagnosed(tmp_path):
    write_rollout(tmp_path,[snapshot(0),snapshot(100)])
    batch=collect(tmp_path)
    assert not batch.events
    assert batch.diagnostics


def test_invalid_response_payload_does_not_fall_back_to_cumulative_totals(tmp_path):
    write_rollout(tmp_path,[metadata(),context(),snapshot(0),snapshot(500),
        dict(type='token_usage_record',timestamp='2026-10-08T12:01:00Z',payload=None)])
    batch=collect(tmp_path)
    assert not batch.events
    assert batch.coverage[0].status == 'partial'
    assert batch.diagnostics


def test_disappearing_file_does_not_abort_scan(tmp_path,monkeypatch):
    from pathlib import Path
    gone=write_rollout(tmp_path,[metadata()],'gone.jsonl')
    write_rollout(tmp_path,[metadata(),context(),usage_row('r1','2026-10-08T12:01:00Z',100)],'good.jsonl')
    real=Path.stat
    def stat_path(path,*args,**kwargs):
        if path == gone:
            raise FileNotFoundError('disappeared')
        return real(path,*args,**kwargs)
    monkeypatch.setattr(Path,'stat',stat_path)
    batch=collect(tmp_path)
    assert len(batch.events) == 1
    assert batch.diagnostics


def test_conversation_items_are_streamed_and_never_enter_batch(tmp_path):
    path=write_rollout(tmp_path,[metadata(),context()])
    with path.open('a') as stream:
        for _ in range(5000):
            stream.write(json.dumps(dict(type='response_item',payload=dict(type='message',content='private text '*100)))+'\n')
        stream.write(json.dumps(usage_row('r1','2026-10-08T12:01:00Z',100))+'\n')
    batch=collect(tmp_path)
    assert len(batch.events) == 1
    assert batch.sessions[0].input_tokens == 100
    assert 'private text' not in repr(batch)
