"""Helpers shared by multiple commands."""
from __future__ import annotations

import sys

from src.config import Config
from src.stores.registry import instantiate_store


def load_remote_stores(cfg: Config) -> list:
    """Instantiate configured remote stores, warning on failures."""
    stores = []
    for sc in cfg.remote_stores:
        try:
            stores.append(instantiate_store(sc.name, sc.params, sc.class_path))
        except Exception as exc:
            print(f"Warning: could not load store {sc.name!r}: {exc}", file=sys.stderr)
    return stores


def run_sync(
    sqlite_store,
    remote_stores: list,
    dry_run: bool,
) -> dict:
    """Core sync logic — separated for testability.

    Returns a dict: {store_name: {"pushed": N, "failed": bool} | {"pending": N}}
    """
    from src.usage import CollectionBatch
    result = {}
    for store in remote_stores:
        capable = callable(getattr(store,'upsert_events',None)) and getattr(store,'supports_usage_events',True)
        sends_coverage = capable and callable(getattr(store,'upsert_session_batch',None))
        pending_method = getattr(sqlite_store,'unsynced_with_coverage_for',None) if sends_coverage else None
        pending = pending_method(store.name) if callable(pending_method) else sqlite_store.unsynced_for(store.name)
        events = sqlite_store.unsynced_events_for(store.name) if callable(getattr(sqlite_store,'unsynced_events_for',None)) else []
        info = {'pending':len(pending),'events_pending':len(events)} if dry_run else {
            'pushed':0,'failed':False,'events_pushed':0,'events_pending':len(events)}
        result[store.name]=info
        try:
            if dry_run:
                continue
            if pending:
                try:
                    if sends_coverage:
                        coverage = sqlite_store.coverage_for_sessions(pending) if callable(getattr(sqlite_store,'coverage_for_sessions',None)) else ()
                        sent_batch=CollectionBatch(tuple(pending),coverage=coverage)
                        store.upsert_session_batch(sent_batch)
                    else:
                        store.upsert(pending)
                    info['pushed']=len(pending)
                except Exception as exc:
                    info.update(failed=True,error=str(exc))
                    print(f'Warning [{store.name}]: {exc}',file=sys.stderr)
                else:
                    try:
                        if sends_coverage and callable(getattr(sqlite_store,'mark_session_batch_synced',None)):
                            sqlite_store.mark_session_batch_synced(sent_batch,store.name)
                        else:
                            sqlite_store.mark_synced(pending,store.name)
                    except Exception as exc:
                        print(f'Warning [sync_log:{store.name}]: {exc}',file=sys.stderr)
            if events:
                if not capable:
                    print(f'Warning [{store.name}]: usage events were not synchronized; store has no enabled event capability',file=sys.stderr)
                else:
                    try:
                        store.upsert_events(events)
                        info['events_pushed']=len(events)
                    except Exception as exc:
                        info.update(failed=True,error=str(exc))
                        print(f'Warning [{store.name}:events]: {exc}',file=sys.stderr)
                    else:
                        try:
                            sqlite_store.mark_events_synced(events,store.name)
                        except Exception as exc:
                            print(f'Warning [event_sync_log:{store.name}]: {exc}',file=sys.stderr)
                info['events_pending']=len(sqlite_store.unsynced_events_for(store.name))
        finally:
            try:
                store.close()
            except Exception:
                pass
    return result
