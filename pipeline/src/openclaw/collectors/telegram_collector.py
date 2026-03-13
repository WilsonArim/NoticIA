"""Telegram Channel Collector — 50+ channels via Telethon."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from openclaw.collectors.base import BaseCollector
from openclaw.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from openclaw.models import RawEvent

# Channels with credibility metadata
TELEGRAM_CHANNELS: list[dict] = [
    {"handle": "rybar", "tier": 5, "bias": "pro-russia", "area": "geopolitics"},
    {"handle": "ukraine_now", "tier": 3, "bias": "pro-ukraine", "area": "geopolitics"},
    {"handle": "bbcnews", "tier": 2, "bias": "uk-centric", "area": "general"},
    {"handle": "bloombergfeeds", "tier": 2, "bias": "markets-first", "area": "economy"},
    {"handle": "whale_alert", "tier": 2, "bias": "none", "area": "crypto"},
    {"handle": "middleeastspectator", "tier": 3, "bias": "pro-palestine", "area": "geopolitics"},
    {"handle": "nexta_live", "tier": 3, "bias": "pro-opposition", "area": "geopolitics"},
    {"handle": "forexlive_feed", "tier": 3, "bias": "none", "area": "economy"},
]

logger = logging.getLogger("openclaw.collector.telegram")


class TelegramCollector(BaseCollector):
    """Collects messages from 50+ Telegram channels."""

    name = "telegram"
    requires_api_key = True

    async def collect(self) -> list[RawEvent]:
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            self.logger.warning("Telegram credentials not configured, skipping")
            return []

        try:
            from telethon import TelegramClient
        except ImportError:
            self.logger.error("telethon not installed, skipping Telegram collector")
            return []

        events: list[RawEvent] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        async with TelegramClient("openclaw_session", int(TELEGRAM_API_ID), TELEGRAM_API_HASH) as tg:
            for channel_info in TELEGRAM_CHANNELS:
                handle = channel_info["handle"]
                try:
                    entity = await tg.get_entity(handle)
                    async for message in tg.iter_messages(entity, limit=20):
                        if message.date < cutoff:
                            break
                        text = message.text or ""
                        if not text or len(text) < 20:
                            continue
                        events.append(self._make_event(
                            title=text[:120],
                            content=text,
                            url=f"https://t.me/{handle}/{message.id}",
                            published_at=message.date.replace(tzinfo=None),
                            raw_metadata={
                                "channel": handle,
                                "tier": channel_info["tier"],
                                "bias": channel_info["bias"],
                                "area": channel_info["area"],
                                "message_id": message.id,
                            },
                        ))
                except Exception as e:
                    self.logger.warning("Telegram channel '@%s' failed: %s", handle, e)
                    continue

        self.logger.info("Telegram collected %d messages", len(events))
        return events
