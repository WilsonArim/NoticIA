"""GDELT v2 API Collector — 14 queries, public API, no auth."""
from __future__ import annotations

import asyncio
from datetime import datetime

from openclaw.collectors.base import BaseCollector
from openclaw.config import GDELT_QUERIES
from openclaw.models import RawEvent

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTCollector(BaseCollector):
    """Collects news events from GDELT v2 API."""

    name = "gdelt"
    requires_api_key = False

    async def collect(self) -> list[RawEvent]:
        """Run all 14 area queries in parallel."""
        client = await self.get_client()
        tasks = [
            self._query_area(client, area, query)
            for area, query in GDELT_QUERIES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        events: list[RawEvent] = []
        for area, result in zip(GDELT_QUERIES.keys(), results):
            if isinstance(result, Exception):
                self.logger.warning("GDELT query '%s' failed: %s", area, result)
                continue
            events.extend(result)
        self.logger.info("GDELT collected %d events across %d areas", len(events), len(GDELT_QUERIES))
        return events

    async def _query_area(self, client, area: str, query: str) -> list[RawEvent]:
        """Query GDELT for a single area."""
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": "50",
            "format": "json",
        }
        try:
            resp = await client.get(GDELT_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.error("GDELT request failed for '%s': %s", area, e)
            return []

        articles = data.get("articles", [])
        events: list[RawEvent] = []
        for art in articles:
            url = art.get("url", "")
            title = art.get("title", "")
            if not url or not title:
                continue
            # GDELT limitation: content = title (no body). Crawl4AI enrichment needed.
            events.append(self._make_event(
                title=title,
                content=title,  # Bug #2: needs Crawl4AI enrichment
                url=url,
                published_at=self._parse_date(art.get("seendate", "")),
                raw_metadata={
                    "domain": art.get("domain", ""),
                    "language": art.get("language", ""),
                    "sourcecountry": art.get("sourcecountry", ""),
                    "area": area,
                    "needs_enrichment": True,
                },
            ))
        return events

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse GDELT date format (YYYYMMDDTHHmmSS)."""
        try:
            return datetime.strptime(date_str[:15], "%Y%m%dT%H%M%S")
        except (ValueError, IndexError):
            return datetime.utcnow()
