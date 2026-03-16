"""Collectors — 4 data source collectors for the OpenClaw pipeline."""
from openclaw.collectors.base import BaseCollector
from openclaw.collectors.gdelt import GDELTCollector
from openclaw.collectors.rss import RSSCollector
from openclaw.collectors.telegram_collector import TelegramCollector
from openclaw.collectors.crawl4ai_collector import Crawl4AICollector


def create_all_collectors() -> list[BaseCollector]:
    """Factory: create all enabled collectors based on env config."""
    from openclaw.config import TELEGRAM_API_ID, TELEGRAM_API_HASH

    collectors: list[BaseCollector] = [
        GDELTCollector(),
        RSSCollector(),
        Crawl4AICollector(),
    ]
    if TELEGRAM_API_ID and TELEGRAM_API_HASH:
        collectors.append(TelegramCollector())
    return collectors


__all__ = [
    "BaseCollector", "GDELTCollector",
    "RSSCollector", "TelegramCollector",
    "Crawl4AICollector", "create_all_collectors",
]
