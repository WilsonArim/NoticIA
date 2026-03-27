#!/usr/bin/env python3
"""
Standalone Telegram Collector — Curador de Noticias
====================================================
Recolhe mensagens de 1278 canais Telegram via Telethon e insere
directamente na intake_queue do Supabase.

Arquitectura:
  Telegram API (Telethon) → dedup → intake_queue (status='pending')
  A partir dai, o pipeline Cowork trata de tudo:
    pipeline-triagem → agente-fact-checker → pipeline-escritor

Rotacao por prioridade:
  - Tier 1-2: verificados em TODOS os ciclos
  - Tier 3-4: 1/3 dos canais por ciclo (rotacao)
  - Tier 5: 1/5 dos canais por ciclo (rotacao lenta)

Uso local:  python collector.py
Uso server: docker run curador-telegram (ver Dockerfile)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
)

from channels import TELEGRAM_CHANNELS

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
PUBLISH_API_KEY = os.getenv("PUBLISH_API_KEY", "")

# Collection settings
CYCLE_INTERVAL_MINUTES = int(os.getenv("CYCLE_INTERVAL_MINUTES", "5"))
MESSAGE_LOOKBACK_HOURS = int(os.getenv("MESSAGE_LOOKBACK_HOURS", "2"))
MAX_MESSAGES_PER_CHANNEL = int(os.getenv("MAX_MESSAGES_PER_CHANNEL", "20"))
MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "20"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "5"))
DELAY_BETWEEN_CHANNELS = float(os.getenv("DELAY_BETWEEN_CHANNELS", "0.5"))

# Session file for Telethon (persists auth between restarts)
SESSION_DIR = Path(__file__).parent / "sessions"
SESSION_DIR.mkdir(exist_ok=True)
SESSION_FILE = str(SESSION_DIR / "curador_telegram")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("telegram-collector")

# Invalid channels tracker
INVALID_CHANNELS_FILE = Path(__file__).parent / "invalid_channels.txt"
_invalid_channels: set[str] = set()


def _record_invalid_channel(handle: str, reason: str) -> None:
    """Track channels that don't exist or are inaccessible."""
    _invalid_channels.add(handle)
    # Append to file immediately (deduped on read)
    try:
        with open(INVALID_CHANNELS_FILE, "a") as f:
            f.write(f"{handle}\t{reason}\n")
    except PermissionError:
        logger.warning("Cannot write to %s (permission denied) — channel tracked in memory only", INVALID_CHANNELS_FILE)


def save_invalid_channels_report() -> None:
    """Write a clean, deduplicated list of invalid channels."""
    if not _invalid_channels:
        return
    # Read existing entries to merge
    existing: dict[str, str] = {}
    if INVALID_CHANNELS_FILE.exists():
        for line in INVALID_CHANNELS_FILE.read_text().strip().splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                existing[parts[0]] = parts[1]
    # Write clean file
    with open(INVALID_CHANNELS_FILE, "w") as f:
        f.write(f"# Invalid Telegram channels — auto-detected\n")
        f.write(f"# {len(existing)} channels | Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"# Format: handle<TAB>reason\n\n")
        for handle in sorted(existing):
            f.write(f"{handle}\t{existing[handle]}\n")
    logger.info(
        "Invalid channels report: %d total (saved to %s)",
        len(existing),
        INVALID_CHANNELS_FILE.name,
    )


# Graceful shutdown
_shutdown = asyncio.Event()


def _handle_signal(sig: int, _frame) -> None:
    logger.info("Received signal %s, shutting down gracefully...", sig)
    _shutdown.set()


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ROTATION SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_cycle_counter = 0


def get_channels_for_cycle() -> list[dict]:
    """
    Priority-based rotation:
    - Tier 1-2: EVERY cycle (always fresh)
    - Tier 3-4: 1/3 of channels per cycle (full rotation every 3 cycles = 15 min)
    - Tier 5: 1/5 of channels per cycle (full rotation every 5 cycles = 25 min)
    """
    global _cycle_counter
    _cycle_counter += 1

    selected = []
    tier_12 = [ch for ch in TELEGRAM_CHANNELS if ch["tier"] in (1, 2)]
    tier_34 = [ch for ch in TELEGRAM_CHANNELS if ch["tier"] in (3, 4)]
    tier_5 = [ch for ch in TELEGRAM_CHANNELS if ch["tier"] == 5]

    # Tier 1-2: always all
    selected.extend(tier_12)

    # Tier 3-4: rotate in 3 slices
    if tier_34:
        slice_idx = _cycle_counter % 3
        chunk_size = len(tier_34) // 3 + 1
        start = slice_idx * chunk_size
        selected.extend(tier_34[start : start + chunk_size])

    # Tier 5: rotate in 5 slices
    if tier_5:
        slice_idx = _cycle_counter % 5
        chunk_size = len(tier_5) // 5 + 1
        start = slice_idx * chunk_size
        selected.extend(tier_5[start : start + chunk_size])

    return selected


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEDUPLICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_seen_urls: set[str] = set()
_MAX_SEEN = 50_000  # prevent unbounded memory growth


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def is_duplicate(url: str) -> bool:
    h = _url_hash(url)
    if h in _seen_urls:
        return True
    if len(_seen_urls) >= _MAX_SEEN:
        # Evict oldest half (approximation — set has no order, but
        # this prevents unbounded growth; real dedup is in DB)
        to_remove = list(_seen_urls)[: _MAX_SEEN // 2]
        for item in to_remove:
            _seen_urls.discard(item)
    _seen_urls.add(h)
    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SUPABASE CLIENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
            )
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


def check_existing_urls(urls: list[str]) -> set[str]:
    """Check which URLs already exist in intake_queue to avoid DB-level duplicates."""
    if not urls:
        return set()
    try:
        sb = get_supabase()
        result = sb.table("intake_queue").select("url").in_("url", urls).execute()
        return {row["url"] for row in result.data}
    except Exception as e:
        logger.warning("Failed to check existing URLs: %s", e)
        return set()


def insert_to_intake_queue(messages: list[dict]) -> int:
    """Insert messages into intake_queue. Returns number of inserted rows."""
    if not messages:
        return 0
    sb = get_supabase()
    inserted = 0
    # Insert in batches of 25 to avoid payload limits
    for i in range(0, len(messages), 25):
        batch = messages[i : i + 25]
        try:
            result = sb.table("intake_queue").insert(batch).execute()
            inserted += len(result.data)
        except Exception as e:
            logger.error("Failed to insert batch %d: %s", i // 25, e)
            # Try inserting one by one to skip duplicates
            for msg in batch:
                try:
                    sb.table("intake_queue").insert(msg).execute()
                    inserted += 1
                except Exception as e2:
                    logger.debug("Skipped duplicate or error: %s", e2)
    return inserted


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AREA MAPPING (Telegram areas → intake_queue areas)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AREA_MAP = {
    "general": "geopolitica",
    "defense": "defesa",
    "geopolitics": "geopolitica",
    "intl_politics": "politica_intl",
    "economy": "economia",
    "crypto": "economia",
    "tech": "tecnologia",
    "ai": "tecnologia",
    "cyber": "tecnologia",
    "health": "saude",
    "science": "ciencia",
    "energy": "energia",
    "environment": "ambiente",
    "sports": "desporto",
    "human_rights": "sociedade",
    "portugal": "portugal",
    "cplp": "portugal",
    "culture": "cultura",
    "regulation": "regulacao",
}


def map_area(telegram_area: str) -> str:
    """Map Telegram channel area to intake_queue area."""
    return AREA_MAP.get(telegram_area, "geopolitica")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TELEGRAM COLLECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def collect_cycle() -> dict:
    """Run one collection cycle. Returns stats dict."""
    channels = get_channels_for_cycle()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MESSAGE_LOOKBACK_HOURS)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    stats = {
        "channels_checked": 0,
        "messages_found": 0,
        "duplicates_skipped": 0,
        "inserted": 0,
        "errors": 0,
        "flood_wait": False,
        "flood_wait_seconds": 0,
        "flood_channels": 0,
    }

    messages_to_insert: list[dict] = []
    urls_to_check: list[str] = []

    logger.info(
        "Starting cycle #%d — checking %d channels (Tier 1-2: all, Tier 3-5: rotation)",
        _cycle_counter + 1,
        len(channels),
    )

    async with TelegramClient(
        SESSION_FILE, TELEGRAM_API_ID, TELEGRAM_API_HASH
    ) as tg:
        for channel_info in channels:
            if _shutdown.is_set():
                logger.info("Shutdown requested, stopping collection")
                break

            handle = channel_info["handle"]
            async with semaphore:
                try:
                    entity = await tg.get_entity(handle)
                    stats["channels_checked"] += 1

                    async for message in tg.iter_messages(
                        entity, limit=MAX_MESSAGES_PER_CHANNEL
                    ):
                        if message.date.replace(tzinfo=timezone.utc) < cutoff:
                            break

                        text = message.text or ""
                        if len(text) < MIN_TEXT_LENGTH:
                            continue

                        url = f"https://t.me/{handle}/{message.id}"

                        # In-memory dedup
                        if is_duplicate(url):
                            stats["duplicates_skipped"] += 1
                            continue

                        stats["messages_found"] += 1
                        urls_to_check.append(url)
                        messages_to_insert.append(
                            {
                                "title": text[:200].strip(),
                                "content": text,
                                "url": url,
                                "area": map_area(channel_info["area"]),
                                "score": _calculate_initial_score(channel_info),
                                "priority": _estimate_priority(channel_info, text),
                                "status": "pending",
                                "metadata": {
                                    "source_collector": "telegram",
                                    "channel": handle,
                                    "tier": channel_info["tier"],
                                    "bias": channel_info["bias"],
                                    "telegram_area": channel_info["area"],
                                    "message_id": message.id,
                                },
                            }
                        )

                except FloodWaitError as e:
                    if e.seconds <= 120:
                        # Short wait — sleep it off and continue
                        logger.info(
                            "Flood-wait %ds on @%s — waiting then continuing",
                            e.seconds,
                            handle,
                        )
                        await asyncio.sleep(e.seconds + 1)
                        stats["errors"] += 1
                    else:
                        # Long wait — skip this channel, continue with others
                        logger.warning(
                            "Flood-wait %ds on @%s — skipping channel, continuing cycle",
                            e.seconds,
                            handle,
                        )
                        _record_invalid_channel(handle, f"FloodWait_{e.seconds}s")
                        stats["flood_wait"] = True
                        stats["flood_wait_seconds"] = max(stats["flood_wait_seconds"], e.seconds)
                        stats["flood_channels"] += 1
                        stats["errors"] += 1

                        # GLOBAL BACK-OFF: if >10 channels hit flood-wait, abort cycle early
                        if stats["flood_channels"] >= 10:
                            logger.warning(
                                "GLOBAL FLOOD-WAIT detected (%d channels, max %ds) — aborting cycle early",
                                stats["flood_channels"], stats["flood_wait_seconds"],
                            )
                            break

                except (ChannelPrivateError, UsernameNotOccupiedError, UsernameInvalidError) as e:
                    reason = type(e).__name__
                    logger.debug("Channel @%s inaccessible: %s", handle, reason)
                    _record_invalid_channel(handle, reason)
                    stats["errors"] += 1

                except Exception as e:
                    error_msg = str(e)
                    logger.warning("Channel @%s failed: %s", handle, error_msg)
                    # Track "No user has" and "Cannot find" as invalid
                    if "No user has" in error_msg or "Cannot find" in error_msg:
                        _record_invalid_channel(handle, error_msg)
                    stats["errors"] += 1

                await asyncio.sleep(DELAY_BETWEEN_CHANNELS)

    # DB-level dedup: check which URLs already exist
    if messages_to_insert:
        existing_urls = check_existing_urls(urls_to_check)
        if existing_urls:
            before = len(messages_to_insert)
            messages_to_insert = [
                m for m in messages_to_insert if m["url"] not in existing_urls
            ]
            stats["duplicates_skipped"] += before - len(messages_to_insert)

        # Insert new messages
        stats["inserted"] = insert_to_intake_queue(messages_to_insert)

    return stats


def _calculate_initial_score(channel_info: dict) -> float:
    """Initial relevance score based on channel credibility tier."""
    tier_scores = {1: 0.9, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.25}
    return tier_scores.get(channel_info["tier"], 0.3)


def _estimate_priority(channel_info: dict, text: str) -> str:
    """Estimate priority based on tier + content signals."""
    text_lower = text.lower()
    # P1 breaking signals
    breaking_keywords = [
        "breaking", "urgente", "just in", "alert", "ataque", "attack",
        "explosion", "killed", "mortos", "war", "guerra", "missile",
        "nuclear", "earthquake", "tsunami", "coup", "golpe",
    ]
    if channel_info["tier"] <= 2 and any(kw in text_lower for kw in breaking_keywords):
        return "p1"
    if channel_info["tier"] <= 2:
        return "p2"
    return "p3"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOG TO SUPABASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def log_pipeline_run(stats: dict) -> None:
    """Log collection stats to pipeline_runs table."""
    try:
        sb = get_supabase()
        sb.table("pipeline_runs").insert(
            {
                "stage": "collect_telegram",
                "status": "completed",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": stats["channels_checked"],
                "events_out": stats["inserted"],
                "metadata": {
                    "source": "telegram-standalone",
                    "messages_found": stats["messages_found"],
                    "duplicates_skipped": stats["duplicates_skipped"],
                    "errors": stats["errors"],
                    "flood_wait": stats["flood_wait"],
                },
            }
        ).execute()
    except Exception as e:
        logger.warning("Failed to log pipeline run: %s", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def main() -> None:
    """Run collection cycles on interval until shutdown."""
    logger.info("=" * 60)
    logger.info("Curador de Noticias — Telegram Collector")
    logger.info("Channels: %d | Cycle: every %d min | Lookback: %dh",
                len(TELEGRAM_CHANNELS), CYCLE_INTERVAL_MINUTES, MESSAGE_LOOKBACK_HOURS)
    logger.info("=" * 60)

    # Validate config
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
        sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        sys.exit(1)

    while not _shutdown.is_set():
        stats: dict = {}
        try:
            stats = await collect_cycle()
            logger.info(
                "Cycle complete — checked: %d channels | found: %d msgs | "
                "inserted: %d | dupes: %d | errors: %d%s",
                stats["channels_checked"],
                stats["messages_found"],
                stats["inserted"],
                stats["duplicates_skipped"],
                stats["errors"],
                " | FLOOD-WAIT" if stats["flood_wait"] else "",
            )
            log_pipeline_run(stats)
            save_invalid_channels_report()

        except Exception as e:
            logger.error("Cycle failed: %s", e, exc_info=True)

        # If global flood-wait was detected, sleep for the flood duration instead of normal interval
        if stats.get("flood_channels", 0) >= 10 and stats.get("flood_wait_seconds", 0) > 0:
            wait_secs = min(stats["flood_wait_seconds"], 7200)  # cap at 2 hours
            logger.warning(
                "Global flood-wait: sleeping %d seconds (%.1f hours) before next cycle",
                wait_secs, wait_secs / 3600,
            )
            try:
                await asyncio.wait_for(_shutdown.wait(), timeout=wait_secs)
                break
            except asyncio.TimeoutError:
                logger.info("Flood-wait sleep complete, resuming collection")
                continue

        # Wait for next cycle (or shutdown)
        try:
            await asyncio.wait_for(
                _shutdown.wait(),
                timeout=CYCLE_INTERVAL_MINUTES * 60,
            )
            # If we get here, shutdown was requested
            break
        except asyncio.TimeoutError:
            # Normal: timeout means it's time for next cycle
            pass

    logger.info("Telegram collector stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
