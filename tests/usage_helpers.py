# tests/usage_helpers.py
def event(sid='s1', eid='r1', day='2026-10-08', tokens=100, model='gpt-5.3-codex'):
    from src.usage import UsageEvent
    return UsageEvent(session_id=sid, source='codex_cli', event_id=eid, model=model,
        timestamp=f'{day}T12:00:00+00:00', date=day, utc_offset_minutes=0,
        input_tokens=tokens, response_id=eid)
