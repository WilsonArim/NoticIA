"""RSS Feed Collector — 80+ feeds including X/Twitter RSS bridges."""
from __future__ import annotations

import asyncio
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from openclaw.collectors.base import BaseCollector
from openclaw.models import RawEvent

# Core RSS feeds (subset — full list in config)
DEFAULT_FEEDS: dict[str, str] = {
    "BBC News World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "NY Times World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Reuters World": "https://feeds.reuters.com/reuters/worldNews",
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "TechCrunch": "https://techcrunch.com/feed/",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "WHO News": "https://www.who.int/rss-feeds/news-english.xml",
    "Carbon Brief": "https://www.carbonbrief.org/feed/",
    "Foreign Affairs": "https://www.foreignaffairs.com/rss.xml",
    "Breaking Defense": "https://breakingdefense.com/feed/",
    "Público PT": "https://www.publico.pt/rss",
    "Observador PT": "https://feeds.observador.pt/rss",
    "BBC Sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "Nature": "https://www.nature.com/nature.rss",
    "Phys.org": "https://phys.org/rss-feed/",
    "Oilprice": "https://oilprice.com/rss/main",
    "STAT News": "https://www.statnews.com/feed/",
    "SCOTUSblog": "https://www.scotusblog.com/feed/",
    "The Intercept": "https://theintercept.com/feed/?rss",
    "Mongabay": "https://news.mongabay.com/feed/",
    "Decrypt": "https://decrypt.co/feed",
}


class RSSCollector(BaseCollector):
    """Collects from 80+ RSS feeds including X/Twitter bridges."""

    name = "rss"
    requires_api_key = False

    def __init__(self, feeds: dict[str, str] | None = None) -> None:
        super().__init__()
        self.feeds = feeds or DEFAULT_FEEDS

    async def collect(self) -> list[RawEvent]:
        tasks = [
            self._fetch_feed(name, url)
            for name, url in self.feeds.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        events: list[RawEvent] = []
        for name, result in zip(self.feeds.keys(), results):
            if isinstance(result, Exception):
                self.logger.warning("RSS feed '%s' failed: %s", name, result)
                continue
            events.extend(result)
        self.logger.info("RSS collected %d events from %d feeds", len(events), len(self.feeds))
        return events

    async def _fetch_feed(self, name: str, url: str) -> list[RawEvent]:
        client = await self.get_client()
        try:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
        except Exception as e:
            self.logger.debug("Failed to fetch RSS '%s': %s", name, e)
            return []

        events: list[RawEvent] = []
        for entry in feed.entries[:50]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            if not title or not link:
                continue
            content = entry.get("summary", "") or entry.get("description", "") or title
            event = self._make_event(
                title=title,
                content=content,
                url=link,
                published_at=self._parse_rss_date(entry),
                raw_metadata={"feed_name": name, "feed_url": url},
            )
            if event is not None:
                events.append(event)
        return events

    @staticmethod
    def _parse_rss_date(entry) -> datetime | None:
        for field in ("published_parsed", "updated_parsed"):
            parsed = entry.get(field)
            if parsed:
                try:
                    return datetime(*parsed[:6])
                except (TypeError, ValueError):
                    continue
        for field in ("published", "updated"):
            raw = entry.get(field, "")
            if raw:
                try:
                    return parsedate_to_datetime(raw)
                except (TypeError, ValueError):
                    continue
        return None
