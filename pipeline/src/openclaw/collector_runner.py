"""
Collector Runner — executa RSS + GDELT collectors e insere raw_events no Supabase.

Chamado pelo scheduler a cada 15 minutos. Cada collector produz RawEvent objects
que são inseridos na tabela raw_events para serem processados pelo dispatcher.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import timezone

from supabase import create_client

from openclaw.agents.dispatcher import _title_hash

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def _insert_raw_events(events) -> int:
    """Insert RawEvent objects into the raw_events table. Returns count inserted."""
    if not events:
        return 0

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    inserted = 0

    # Batch insert in groups of 25
    for i in range(0, len(events), 25):
        batch = events[i:i + 25]
        rows = []
        for ev in batch:
            pub_at = ev.published_at
            if pub_at and pub_at.tzinfo is None:
                pub_at = pub_at.replace(tzinfo=timezone.utc)

            # event_hash = sha256(url:source_collector) — matches RawEvent.id generation
            event_hash = hashlib.sha256(
                f"{ev.url}:{ev.source_collector}".encode()
            ).hexdigest()

            # V3: classify source origin for contra-media routing
            source_type = "alternative" if ev.source_collector in ("telegram",) else "media"

            rows.append({
                "event_hash": event_hash,
                "title": ev.title[:500],
                "title_hash": _title_hash(ev.title),
                "content": (ev.content or "")[:5000],
                "url": ev.url,
                "source_collector": ev.source_collector,
                "published_at": pub_at.isoformat() if pub_at else None,
                "raw_metadata": ev.raw_metadata or {},
                "processed": False,
                "source_type": source_type,
            })

        try:
            result = sb.table("raw_events").upsert(
                rows,
                on_conflict="event_hash",
                ignore_duplicates=True,
            ).execute()
            inserted += len(result.data) if result.data else 0
        except Exception as e:
            logger.warning("Failed to insert raw_events batch %d: %s", i // 25, e)
            # Try one by one to skip individual failures
            for row in rows:
                try:
                    sb.table("raw_events").upsert(
                        row,
                        on_conflict="event_hash",
                        ignore_duplicates=True,
                    ).execute()
                    inserted += 1
                except Exception:
                    pass

    return inserted


async def _run_collectors_async() -> dict:
    """Run RSS and GDELT collectors, return stats."""
    from openclaw.collectors.rss import RSSCollector
    from openclaw.collectors.gdelt import GDELTCollector

    stats = {"rss": 0, "gdelt": 0, "inserted": 0, "errors": []}

    # RSS Collector
    rss = RSSCollector()
    try:
        rss_events = await rss.collect()
        stats["rss"] = len(rss_events)
    except Exception as e:
        logger.error("RSS collector failed: %s", e)
        stats["errors"].append(f"rss: {e}")
        rss_events = []
    finally:
        await rss.close()

    # GDELT Collector
    gdelt = GDELTCollector()
    try:
        gdelt_events = await gdelt.collect()
        stats["gdelt"] = len(gdelt_events)
    except Exception as e:
        logger.error("GDELT collector failed: %s", e)
        stats["errors"].append(f"gdelt: {e}")
        gdelt_events = []
    finally:
        await gdelt.close()

    # Merge and insert
    all_events = rss_events + gdelt_events
    if all_events:
        stats["inserted"] = _insert_raw_events(all_events)

    return stats


def run_collectors() -> None:
    """Sync entry point for the scheduler. Runs RSS + GDELT collectors."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Collectors: SUPABASE_URL / SUPABASE_SERVICE_KEY missing — skipping")
        return

    try:
        stats = asyncio.run(_run_collectors_async())
        logger.info(
            "Collectors: RSS=%d, GDELT=%d → inserted %d raw_events",
            stats["rss"], stats["gdelt"], stats["inserted"],
        )
        if stats["errors"]:
            logger.warning("Collector errors: %s", "; ".join(stats["errors"]))
    except Exception as e:
        logger.error("Collector runner failed: %s", e)
