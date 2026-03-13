"""Collectors — 7 data source collectors for the OpenClaw pipeline."""
from openclaw.collectors.base import BaseCollector
from openclaw.collectors.gdelt import GDELTCollector
from openclaw.collectors.event_registry import EventRegistryCollector
from openclaw.collectors.acled import ACLEDCollector
from openclaw.collectors.rss import RSSCollector
from openclaw.collectors.telegram_collector import TelegramCollector
from openclaw.collectors.crawl4ai_collector import Crawl4AICollector


def create_all_collectors() -> list[BaseCollector]:
    """Factory: create all enabled collectors based on env config."""
    from openclaw.config import (
        EVENT_REGISTRY_API_KEY, ACLED_API_KEY, ACLED_EMAIL,
        TELEGRAM_API_ID, TELEGRAM_API_HASH,
    )
    collectors: list[BaseCollector] = [
        GDELTCollector(),
        RSSCollector(),
        Crawl4AICollector(),
    ]
    if EVENT_REGISTRY_API_KEY:
        collectors.append(EventRegistryCollector())
    if ACLED_API_KEY and ACLED_EMAIL:
        collectors.append(ACLEDCollector())
    if TELEGRAM_API_ID and TELEGRAM_API_HASH:
        collectors.append(TelegramCollector())
    return collectors


__all__ = [
    "BaseCollector", "GDELTCollector", "EventRegistryCollector",
    "ACLEDCollector", "RSSCollector", "TelegramCollector",
    "Crawl4AICollector", "create_all_collectors",
]
