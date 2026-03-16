"""Bridge — resolves the gap between raw_events and intake_queue.

Reads unprocessed raw_events from Supabase, scores them using all 14
reporters (keyword matching), inserts qualifying events into intake_queue
with priority (p1/p2/p3), and marks raw_events as processed.

Usage:
    python -m openclaw.bridge              # process unprocessed events
    python -m openclaw.bridge --dry-run    # preview without DB writes
    python -m openclaw.bridge --reset      # reset processed flag first (for testing)
"""
from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from typing import Any

import httpx

from openclaw.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
from openclaw.models import RawEvent
from openclaw.reporters.base import create_all_reporters

logger = logging.getLogger("openclaw.bridge")

# Map reporter area (English) -> scored_events area (lowercase PT, matches DB CHECK constraint)
AREA_DB_MAP: dict[str, str] = {
    "geopolitics": "geopolitica",
    "defense": "defesa",
    "economy": "economia",
    "tech": "tecnologia",
    "energy": "energia",
    "health": "saude",
    "environment": "clima",
    "crypto": "crypto",
    "regulation": "regulacao",
    "portugal": "portugal",
    "science": "ciencia",
    "financial_markets": "financas",
    "society": "sociedade",
    "sports": "desporto",
    "intl_politics": "politica_intl",
    "diplomacy": "diplomacia",
    "defense_strategy": "defesa_estrategica",
    "disinfo": "desinformacao",
    "human_rights": "direitos_humanos",
    "organized_crime": "crime_organizado",
}

# Map for intake_queue area (title case PT)
AREA_INTAKE_MAP: dict[str, str] = {
    "geopolitics": "Geopolitica",
    "defense": "Defesa",
    "economy": "Economia",
    "tech": "Tech",
    "energy": "Energia",
    "health": "Saude",
    "environment": "Ambiente",
    "crypto": "Crypto",
    "regulation": "Regulacao",
    "portugal": "Portugal",
    "science": "Ciencia",
    "financial_markets": "Mercados",
    "society": "Sociedade",
    "sports": "Desporto",
    "intl_politics": "Politica Internacional",
    "diplomacy": "Diplomacia",
    "defense_strategy": "Defesa Estrategica",
    "disinfo": "Desinformacao",
    "human_rights": "Direitos Humanos",
    "organized_crime": "Crime Organizado",
}


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def _parse_datetime(value: str | None) -> datetime:
    """Parse ISO datetime string to naive UTC datetime."""
    if not value:
        return datetime.utcnow()
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Strip timezone for compatibility with score_event() which uses naive utcnow()
    return dt.replace(tzinfo=None)


def db_row_to_raw_event(row: dict[str, Any]) -> RawEvent:
    """Convert a Supabase raw_events row to a RawEvent dataclass."""
    published_at = _parse_datetime(
        row.get("published_at") or row.get("fetched_at") or row.get("created_at")
    )
    return RawEvent(
        source_collector=row["source_collector"],
        title=row.get("title") or "",
        content=row.get("content") or "",
        url=row.get("url") or "",
        published_at=published_at,
        raw_metadata=row.get("raw_metadata") or {},
        id=row["id"],
    )


async def fetch_unprocessed(client: httpx.AsyncClient, limit: int = 200) -> list[dict]:
    """Fetch raw_events where processed = false."""
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/raw_events",
        params={
            "processed": "eq.false",
            "order": "published_at.desc",
            "limit": str(limit),
        },
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_existing_scored_ids(
    client: httpx.AsyncClient, event_ids: list[str]
) -> set[tuple[str, str]]:
    """Get (raw_event_id, area) pairs already in scored_events to avoid duplicates."""
    if not event_ids:
        return set()
    ids_filter = ",".join(event_ids)
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/scored_events",
        params={
            "raw_event_id": f"in.({ids_filter})",
            "select": "raw_event_id,area",
        },
        headers=_headers(),
    )
    resp.raise_for_status()
    return {(r["raw_event_id"], r["area"]) for r in resp.json()}


async def insert_scored_events(client: httpx.AsyncClient, rows: list[dict]) -> int:
    """Insert scored events, returns count inserted."""
    if not rows:
        return 0
    resp = await client.post(
        f"{SUPABASE_URL}/rest/v1/scored_events",
        json=rows,
        headers={**_headers(), "Prefer": "return=minimal"},
    )
    resp.raise_for_status()
    return len(rows)


async def insert_intake_queue(client: httpx.AsyncClient, rows: list[dict]) -> int:
    """Insert events into intake_queue, returns count inserted."""
    if not rows:
        return 0
    resp = await client.post(
        f"{SUPABASE_URL}/rest/v1/intake_queue",
        json=rows,
        headers={**_headers(), "Prefer": "return=minimal"},
    )
    resp.raise_for_status()
    return len(rows)


async def mark_processed(client: httpx.AsyncClient, event_ids: list[str]) -> None:
    """Mark raw_events as processed."""
    if not event_ids:
        return
    ids_filter = ",".join(event_ids)
    resp = await client.patch(
        f"{SUPABASE_URL}/rest/v1/raw_events",
        params={"id": f"in.({ids_filter})"},
        json={"processed": True},
        headers={**_headers(), "Prefer": "return=minimal"},
    )
    resp.raise_for_status()


async def reset_processed(client: httpx.AsyncClient) -> int:
    """Reset all raw_events to processed=false (for testing)."""
    resp = await client.patch(
        f"{SUPABASE_URL}/rest/v1/raw_events",
        params={"processed": "eq.true"},
        json={"processed": False},
        headers={**_headers(), "Prefer": "return=representation"},
    )
    resp.raise_for_status()
    count = len(resp.json())
    logger.info("Reset %d raw_events to processed=false", count)
    return count


async def run_bridge(
    limit: int = 200, dry_run: bool = False, do_reset: bool = False
) -> dict[str, int]:
    """Main bridge: raw_events -> scoring -> scored_events + intake_queue.

    Returns stats dict with fetched, scored, queued counts.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Optional: reset for testing
        if do_reset:
            await reset_processed(client)

        # 1. Fetch unprocessed raw_events
        rows = await fetch_unprocessed(client, limit)
        if not rows:
            logger.info("No unprocessed raw_events found")
            return {"fetched": 0, "scored": 0, "queued": 0}

        logger.info("Fetched %d unprocessed raw_events", len(rows))

        # 2. Convert to RawEvent dataclass
        events = [db_row_to_raw_event(r) for r in rows]
        event_ids = [r["id"] for r in rows]

        # 3. Check existing scored_events to avoid duplicates
        existing_scored = await fetch_existing_scored_ids(client, event_ids)
        logger.info("Found %d existing scored_events entries (will skip)", len(existing_scored))

        # 4. Score with all 14 reporters
        reporters = create_all_reporters()

        # Track best score per event (event may match multiple reporters)
        best_per_event: dict[str, dict[str, Any]] = {}
        new_scored_rows: list[dict] = []

        for reporter in reporters:
            scored = reporter.score_events(events)
            for se in scored:
                area_pt = AREA_DB_MAP.get(se.area, se.area)

                # Skip if already scored for this area
                if (se.raw_event.id, area_pt) not in existing_scored:
                    new_scored_rows.append({
                        "raw_event_id": se.raw_event.id,
                        "area": area_pt,
                        "reporter_score": round(se.score, 4),
                        "matched_keywords": se.matched_keywords,
                    })

                # Track best score per event for intake_queue
                existing = best_per_event.get(se.raw_event.id)
                if not existing or se.score > existing["score"]:
                    best_per_event[se.raw_event.id] = {
                        "score": se.score,
                        "area": se.area,
                        "priority": se.priority.lower(),
                        "keywords": se.matched_keywords,
                        "raw_event": se.raw_event,
                    }

        logger.info(
            "Scoring complete: %d new scored_events, %d unique events qualified",
            len(new_scored_rows),
            len(best_per_event),
        )

        # 5. Build intake_queue entries for qualifying events
        intake_rows: list[dict] = []
        for event_id, best in best_per_event.items():
            ev: RawEvent = best["raw_event"]
            area_intake = AREA_INTAKE_MAP.get(best["area"], best["area"])
            intake_rows.append({
                "source_event_id": event_id,
                "title": ev.title,
                "content": ev.content[:5000],  # cap content length
                "url": ev.url,
                "area": area_intake,
                "score": round(best["score"], 4),
                "priority": best["priority"],
                "status": "pending",
                "metadata": {
                    "matched_keywords": best["keywords"],
                    "source_collector": ev.source_collector,
                    "bridge_version": "v1",
                },
            })

        stats = {
            "fetched": len(rows),
            "scored": len(new_scored_rows),
            "queued": len(intake_rows),
        }

        if dry_run:
            logger.info("DRY RUN - no DB writes")
            for iq in intake_rows:
                logger.info(
                    "  -> [%s] %s (score=%.3f, area=%s)",
                    iq["priority"],
                    iq["title"][:60],
                    iq["score"],
                    iq["area"],
                )
            return stats

        # 6. Insert into DB
        inserted_scored = await insert_scored_events(client, new_scored_rows)
        inserted_intake = await insert_intake_queue(client, intake_rows)
        logger.info("Inserted %d scored_events, %d intake_queue items", inserted_scored, inserted_intake)

        # 7. Mark raw_events as processed
        await mark_processed(client, event_ids)
        logger.info("Marked %d raw_events as processed", len(event_ids))

        logger.info("Bridge complete: %s", stats)
        return stats


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    dry = "--dry-run" in sys.argv
    do_reset = "--reset" in sys.argv
    result = asyncio.run(run_bridge(dry_run=dry, do_reset=do_reset))
    print(f"\nResult: {result}")
