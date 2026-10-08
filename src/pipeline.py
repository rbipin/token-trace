"""Fluent pipeline wiring collectors to stores."""

from __future__ import annotations

import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from datetime import date
from typing import List

from .collectors.base import ActivityCollector
from .middleware.base import RecordMiddleware
from .models import DEFAULT_CONTEXT, SessionRecord, merge_records
from .stores import SessionStore
from .usage import CollectionBatch, UsageEvent


@dataclass(frozen=True)
class RunResult:
    """Outcome of a single pipeline run."""

    records_written: int
    collectors_run: int
    errors: List[str] = field(default_factory=list)
    stores_failed: List[str] = field(default_factory=list)
    events_written: int = 0


class TrackerPipeline:
    """Builds and runs a collection pass.

    Usage::

        (TrackerPipeline()
            .add(ClaudeCliCollector(...))
            .since(start)
            .stores(SqliteStore(db), remote_store)
            .run())
    """

    def __init__(self) -> None:
        self._collectors: list[ActivityCollector] = []
        self._since: date | None = None
        self._stores: list[SessionStore] = []
        self._context: str = DEFAULT_CONTEXT
        self._middlewares: list[RecordMiddleware] = []

    def context(self, label: str) -> "TrackerPipeline":
        """Set the usage context label (e.g. "work" or "personal") stamped on every record."""
        self._context = label
        return self

    def add(self, collector: ActivityCollector) -> "TrackerPipeline":
        self._collectors.append(collector)
        return self

    def middlewares(self, *mw: RecordMiddleware) -> "TrackerPipeline":
        self._middlewares = list(mw)
        return self

    def since(self, start: date) -> "TrackerPipeline":
        self._since = start
        return self

    def stores(self, *stores: SessionStore) -> "TrackerPipeline":
        self._stores = list(stores)
        return self

    def store(self, store: SessionStore) -> "TrackerPipeline":
        warnings.warn(
            "TrackerPipeline.store() is deprecated; use .stores()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.stores(store)

    def run(self) -> RunResult:
        if self._since is None:
            raise ValueError("since(start) must be set before run()")
        if not self._stores:
            raise ValueError("stores(...) must be set before run()")

        records: list[SessionRecord] = []
        events: list[UsageEvent] = []
        coverage = {}
        errors: list[str] = []

        def _collect(collector: ActivityCollector) -> tuple[CollectionBatch, str | None]:
            try:
                if callable(getattr(collector, 'collect_batch', None)):
                    return collector.collect_batch(self._since), None
                return CollectionBatch(sessions=tuple(collector.collect(self._since))), None
            except Exception as exc:
                name = getattr(collector, "source", type(collector).__name__)
                return CollectionBatch(), f"{name}: {exc}"

        with ThreadPoolExecutor(max_workers=max(len(self._collectors), 1)) as pool:
            futures = {pool.submit(_collect, c): c for c in self._collectors}
            for future in as_completed(futures):
                batch, err = future.result()
                records.extend(batch.sessions)
                events.extend(batch.events)
                coverage.update({(c.source,c.session_id): c for c in batch.coverage})
                errors.extend(batch.diagnostics)
                if err:
                    errors.append(err)

        merged = merge_records(records)
        merged = [replace(rec, context=self._context) for rec in merged]

        events = [replace(e,context=self._context) for e in {e.key:e for e in events}.values()]
        for mw in self._middlewares:
            if mw.applies(merged):
                merged = mw.process(merged)
            if callable(getattr(mw, 'process_events', None)):
                events = mw.process_events(events)

        # SQLite (first store) must succeed — exceptions propagate
        events_written = 0
        if callable(getattr(self._stores[0], 'upsert_batch', None)):
            written = self._stores[0].upsert_batch(CollectionBatch(tuple(merged),tuple(events),tuple(coverage.values())))
            events_written = len(events)
        else:
            written = self._stores[0].upsert(merged)
            if events or coverage:
                errors.append(f'{self._stores[0].name}: usage events require batch persistence; only session summaries stored')
        self._stores[0].close()

        # Remotes: parallel, log-and-continue
        stores_failed: list[str] = []

        def _push(store: SessionStore) -> str | None:
            try:
                store.upsert(merged)
                store.close()
            except Exception as exc:
                return f"{store.name}: {exc}"
            if hasattr(self._stores[0], "mark_synced"):
                try:
                    self._stores[0].mark_synced(merged, store.name)
                except Exception as exc:
                    print(f"Warning [sync_log:{store.name}]: {exc}", file=sys.stderr)
            return None

        if len(self._stores) > 1:
            if callable(getattr(self._stores[0],'unsynced_for',None)):
                from .commands.common import run_sync
                synced=run_sync(self._stores[0],self._stores[1:],False)
                stores_failed.extend(f"{name}: {info.get('error','remote sync failed')}" for name,info in synced.items() if info.get('failed'))
            else:
                with ThreadPoolExecutor(max_workers=len(self._stores) - 1) as pool:
                    for err in pool.map(_push, self._stores[1:]):
                        if err:
                            stores_failed.append(err)

        return RunResult(
            records_written=written,
            collectors_run=len(self._collectors),
            events_written=events_written,
            errors=errors,
            stores_failed=stores_failed,
        )
