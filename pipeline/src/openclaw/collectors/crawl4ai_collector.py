"""Crawl4AI Collector — on-demand web scraper for content enrichment."""
from __future__ import annotations

from openclaw.collectors.base import BaseCollector
from openclaw.models import RawEvent


class Crawl4AICollector(BaseCollector):
    """On-demand web scraper for enriching events without body content."""

    name = "crawl4ai"
    requires_api_key = False

    async def collect(self) -> list[RawEvent]:
        """Crawl4AI is on-demand only. Returns empty for scheduled runs."""
        return []

    async def enrich_event(self, event: RawEvent) -> RawEvent:
        """Fetch full article body for events with content == title (GDELT fix)."""
        if event.content and event.content != event.title:
            return event  # Already has content

        try:
            from crawl4ai import AsyncWebCrawler
        except ImportError:
            self.logger.error("crawl4ai not installed, cannot enrich")
            return event

        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=event.url)
                if result and result.markdown:
                    event.content = result.markdown[:5000]  # Cap content length
                    event.raw_metadata["enriched_by"] = "crawl4ai"
                    event.raw_metadata["needs_enrichment"] = False
                    self.logger.debug("Enriched GDELT event: %s", event.title[:60])
        except Exception as e:
            self.logger.warning("Crawl4AI enrichment failed for %s: %s", event.url[:80], e)

        return event
