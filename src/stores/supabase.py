"""Supabase remote store for TokenTracer."""
from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import asdict
from ..usage import UsageEvent, CollectionBatch

from ..models import SessionRecord

try:
    from supabase import create_client as _create_client
except ImportError:
    _create_client = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from supabase import Client


class SupabaseStore:
    """Remote store that upserts SessionRecords into a Supabase table."""

    name = "supabase"

    def __init__(self, url: str, key: str, table: str = "token_sessions", usage_table: str | None = None) -> None:
        self._url = url
        self._key = key
        self._table = table
        self._usage_table = usage_table
        self._client_cache: Client | None = None

    @property
    def _client(self) -> "Client":
        if self._client_cache is None:
            if _create_client is None:
                raise ImportError(
                    "supabase-py is required for SupabaseStore. "
                    "Install with: pip install tokentracer[supabase]"
                )
            self._client_cache = _create_client(self._url, self._key)
        return self._client_cache

    def upsert(self, records: list[SessionRecord]) -> int:
        """Upsert records into Supabase; returns the count submitted."""
        if not records:
            return 0
        rows = [asdict(r) for r in records]
        self._client.table(self._table).upsert(
            rows, on_conflict="session_id,source,model"
        ).execute()
        return len(records)

    @property
    def supports_usage_events(self) -> bool:
        return bool(self._usage_table)

    def upsert_session_batch(self, batch: CollectionBatch) -> int:
        if not self.supports_usage_events:
            return self.upsert(list(batch.sessions))
        if not batch.sessions:
            return 0
        coverage = {(c.source,c.session_id): c for c in batch.coverage}
        rows=[]
        for record in batch.sessions:
            row=asdict(record)
            marker=coverage.get((record.source,record.session_id))
            row['usage_coverage']=marker.status if marker else 'legacy'
            row['usage_coverage_reason']=marker.reason if marker else None
            rows.append(row)
        self._client.table(self._table).upsert(rows,on_conflict='session_id,source,model').execute()
        return len(rows)

    def upsert_events(self, events: list[UsageEvent]) -> int:
        if not self._usage_table:
            raise ValueError('configure usage_table after applying the usage-events migration')
        if not events:
            return 0
        self._client.table(self._usage_table).upsert([asdict(e) for e in events],
            on_conflict='source,session_id,event_id').execute()
        return len(events)

    def close(self) -> None:
        self._client_cache = None
