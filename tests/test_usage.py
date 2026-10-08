from dataclasses import FrozenInstanceError, replace
from zoneinfo import ZoneInfo
import pytest
from src.usage import UsageEvent, UsageCoverage, CollectionBatch, normalize_usage, event_time


def test_cache_and_reasoning_are_subsets():
    counts = normalize_usage(dict(input_tokens=1000, cached_input_tokens=600,
        cache_write_input_tokens=100, output_tokens=200, reasoning_output_tokens=80))
    assert counts == dict(input_tokens=300, cache_read_tokens=600,
        cache_creation_tokens=100, output_tokens=200, reasoning_tokens=80)
    assert sum(counts[k] for k in ('input_tokens','cache_read_tokens','cache_creation_tokens','output_tokens')) == 1200


@pytest.mark.parametrize('value', [-1, True, False, 1.5, '100', None])
@pytest.mark.parametrize('field', ['input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens'])
def test_invalid_counts_are_rejected(field, value):
    with pytest.raises(ValueError):
        normalize_usage({field: value})


@pytest.mark.parametrize('usage', [dict(input_tokens=10,cached_input_tokens=11),
    dict(input_tokens=10,cached_input_tokens=8,cache_write_input_tokens=3),
    dict(output_tokens=10,reasoning_output_tokens=11)])
def test_subsets_cannot_exceed_totals(usage):
    with pytest.raises(ValueError):
        normalize_usage(usage)


def test_missing_optional_counts_are_zero():
    assert normalize_usage({}) == dict(input_tokens=0,output_tokens=0,
        cache_read_tokens=0,cache_creation_tokens=0,reasoning_tokens=0)


@pytest.mark.parametrize('stamp,day,offset', [
    ('2026-10-09T03:59:59Z','2026-10-08',-240),
    ('2026-10-09T04:00:00Z','2026-10-09',-240),
    ('2026-11-01T05:30:00Z','2026-11-01',-240),
    ('2026-11-01T06:30:00Z','2026-11-01',-300),
    ('2026-03-08T06:59:59Z','2026-03-08',-300),
    ('2026-03-08T07:00:00Z','2026-03-08',-240)])
def test_local_day_and_historical_dst(stamp,day,offset):
    utc, actual_day, actual_offset = event_time(stamp,ZoneInfo('America/Detroit'))
    assert actual_day == day
    assert actual_offset == offset
    assert utc.endswith('+00:00')


@pytest.mark.parametrize('stamp',['invalid','2026-10-08','2026-10-08T12:00:00'])
def test_timestamp_requires_timezone(stamp):
    with pytest.raises(ValueError):
        event_time(stamp)


def test_event_is_frozen_and_canonical_alias_preserves_identity():
    e = UsageEvent('s1','codex_cli','response:r1','raw-model','2026-10-08T12:00:00+00:00','2026-10-08',0)
    with pytest.raises(FrozenInstanceError):
        e.input_tokens = 100
    assert replace(e,canonical_model='alias').key == ('codex_cli','s1','response:r1')
    coverage=UsageCoverage('codex_cli','s1','measured')
    batch=CollectionBatch(( ),(e,),(coverage,))
    with pytest.raises(FrozenInstanceError):
        batch.events = ()
