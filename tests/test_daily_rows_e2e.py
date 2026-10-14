import json
import sqlite3
from datetime import date

from src.collectors import ClaudeCliCollector, CodexCliCollector
from src.dashboard import queries
from src.middleware import ModelNormalizeMiddleware
from src.pipeline import TrackerPipeline
from src.stores.sqlite import SqliteStore


def _claude(root):
    folder = root / 'claude' / 'p'
    folder.mkdir(parents=True)
    (folder / 'c1.jsonl').write_text('\n'.join(json.dumps(e) for e in [
        {"type": "assistant", "timestamp": "2026-10-08T10:00:00Z",
         "message": {"model": "claude-sonnet-4-6", "usage": {"input_tokens": 100, "output_tokens": 10}}},
        {"type": "assistant", "timestamp": "2026-10-09T10:00:00Z",
         "message": {"model": "claude-sonnet-4-6", "usage": {"input_tokens": 50, "output_tokens": 5}}},
    ]), encoding='utf-8')
    return root / 'claude'


def _codex(root):
    rollout = root / 'codex' / 'sessions' / 'r.jsonl'
    rollout.parent.mkdir(parents=True)
    rollout.write_text(''.join(json.dumps(r) + '\n' for r in [
        dict(type='session_meta', payload=dict(id='x1', timestamp='2026-10-08T10:00:00Z', source='cli')),
        dict(type='turn_context', payload=dict(turn_id='t1', model='gpt-5.3-codex')),
        dict(type='token_usage_record', timestamp='2026-10-09T10:00:00Z', payload=dict(
            session_id='x1', thread_id='x1', turn_id='t1', response_id='r1',
            usage=dict(input_tokens=70, output_tokens=7))),
    ]), encoding='utf-8')
    return root / 'codex'


def test_collect_twice_keeps_daily_totals(tmp_path):
    claude, codex, db = _claude(tmp_path), _codex(tmp_path), tmp_path / 'usage.db'

    def run():
        return (TrackerPipeline().since(date(2026, 10, 1))
                .add(ClaudeCliCollector(claude)).add(CodexCliCollector(codex))
                .middlewares(ModelNormalizeMiddleware()).stores(SqliteStore(db)).run())

    run()
    run()
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        day8 = queries.summary(conn, 'custom', '2026-10-08', '2026-10-08')
        day9 = queries.summary(conn, 'custom', '2026-10-09', '2026-10-09')
        rows = [tuple(r) for r in conn.execute('SELECT source, date FROM sessions ORDER BY source, date')]
    assert (day8['total_tokens'], day9['total_tokens']) == (110, 132)
    assert (day8['session_count'], day9['session_count']) == (1, 2)
    assert rows == [('claude_cli', '2026-10-08'), ('claude_cli', '2026-10-09'), ('codex_cli', '2026-10-09')]
