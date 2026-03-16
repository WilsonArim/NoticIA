"""GDELT v2 API Collector — sequential queries with rate limiting."""
from __future__ import annotations

import asyncio
import random
from datetime import datetime

from openclaw.collectors.base import BaseCollector
from openclaw.config import GDELT_QUERIES
from openclaw.models import RawEvent

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERY_DELAY_S = 2.0  # Delay between sequential queries
MAX_RETRIES = 3
BASE_BACKOFF_S = 5.0  # Exponential backoff base for 429 errors


class GDELTCollector(BaseCollector):
    """Collects news events from GDELT v2 API."""

    name = "gdelt"
    requires_api_key = False
    _run_count: int = 0  # Alternates odd/even area batches

    async def collect(self) -> list[RawEvent]:
        """Run area queries sequentially with delay to avoid 429."""
        client = await self.get_client()
        areas = list(GDELT_QUERIES.items())

        # Alternate between odd/even indexed areas each run
        self._run_count += 1
        parity = self._run_count % 2
        batch = [a for i, a in enumerate(areas) if i % 2 == parity]
        self.logger.info(
            "GDELT running batch %s (%d/%d areas)",
            "even" if parity == 0 else "odd",
            len(batch),
            len(areas),
        )

        events: list[RawEvent] = []
        for idx, (area, query) in enumerate(batch):
            try:
                result = await self._query_area_with_retry(client, area, query)
                events.extend(result)
            except Exception as e:
                self.logger.warning("GDELT query '%s' failed: %s", area, e)

            # Delay between queries (except last)
            if idx < len(batch) - 1:
                await asyncio.sleep(QUERY_DELAY_S)

        self.logger.info(
            "GDELT collected %d events from %d areas (batch %d)",
            len(events), len(batch), self._run_count,
        )
        return events

    async def _query_area_with_retry(
        self, client, area: str, query: str
    ) -> list[RawEvent]:
        """Query with exponential backoff retry on HTTP 429."""
        for attempt in range(MAX_RETRIES):
            result = await self._query_area(client, area, query, attempt)
            if result is not None:
                return result
        self.logger.warning("GDELT '%s' failed after %d retries", area, MAX_RETRIES)
        return []

    async def _query_area(
        self, client, area: str, query: str, attempt: int = 0
    ) -> list[RawEvent] | None:
        """Query GDELT for a single area. Returns None on 429 to trigger retry."""
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": "50",
            "format": "json",
            "timespan": "72h",
        }
        try:
            resp = await client.get(GDELT_API_URL, params=params)
            if resp.status_code == 429:
                wait = BASE_BACKOFF_S * (2 ** attempt) + random.uniform(0, 2)
                self.logger.warning(
                    "GDELT 429 for '%s', retry %d in %.1fs", area, attempt + 1, wait
                )
                await asyncio.sleep(wait)
                return None  # Signal retry
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
            event = self._make_event(
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
            )
            if event is not None:
                events.append(event)
        return events

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        """Parse GDELT date format (YYYYMMDDTHHmmSS)."""
        try:
            return datetime.strptime(date_str[:15], "%Y%m%dT%H%M%S")
        except (ValueError, IndexError):
            return None
