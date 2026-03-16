"""Event Registry API Collector — rate-limited queries, requires API key."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from openclaw.collectors.base import BaseCollector
from openclaw.config import EVENT_REGISTRY_API_KEY, GDELT_QUERIES
from openclaw.models import RawEvent

ER_API_URL = "https://eventregistry.org/api/v1/article/getArticles"

# Rate-limit settings for free tier
_MAX_CONCURRENT = 2        # max simultaneous requests
_DELAY_BETWEEN_SECS = 1.5  # pause between each query
_RETRY_MAX = 3             # retries on 429
_RETRY_BACKOFF_BASE = 5    # seconds: 5, 10, 20


class EventRegistryCollector(BaseCollector):
    """Collects articles from Event Registry API with rate limiting."""

    name = "event_registry"
    requires_api_key = True

    async def collect(self) -> list[RawEvent]:
        if not EVENT_REGISTRY_API_KEY:
            self.logger.warning("Event Registry API key not configured, skipping")
            return []

        client = await self.get_client()
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
        events: list[RawEvent] = []
        areas = list(GDELT_QUERIES.items())

        for i, (area, query) in enumerate(areas):
            async with semaphore:
                try:
                    result = await self._query_area_with_retry(client, area, query)
                    events.extend(result)
                except Exception as exc:
                    self.logger.warning("ER query '%s' failed: %s", area, exc)

            # Small delay between queries to avoid 429
            if i < len(areas) - 1:
                await asyncio.sleep(_DELAY_BETWEEN_SECS)

        self.logger.info("Event Registry collected %d events", len(events))
        return events

    async def _query_area_with_retry(
        self, client, area: str, query: str
    ) -> list[RawEvent]:
        """Query with exponential backoff on 429 Too Many Requests."""
        for attempt in range(_RETRY_MAX):
            result = await self._query_area(client, area, query, raise_on_429=True)
            if result is not None:
                return result
            # 429 received — backoff and retry
            wait = _RETRY_BACKOFF_BASE * (2 ** attempt)
            self.logger.info(
                "ER 429 on '%s', retry %d/%d in %ds",
                area, attempt + 1, _RETRY_MAX, wait,
            )
            await asyncio.sleep(wait)

        self.logger.warning("ER query '%s' exhausted retries (429)", area)
        return []

    async def _query_area(
        self, client, area: str, query: str, *, raise_on_429: bool = False
    ) -> list[RawEvent] | None:
        """Returns list of events, or None if 429 and raise_on_429 is True."""
        date_start = (datetime.utcnow() - timedelta(hours=72)).strftime("%Y-%m-%d")
        payload = {
            "keyword": query,
            "lang": "eng",
            "articlesCount": 50,
            "articlesSortBy": "date",
            "dateStart": date_start,
            "apiKey": EVENT_REGISTRY_API_KEY,
        }
        try:
            resp = await client.post(ER_API_URL, json=payload)
            if resp.status_code == 429 and raise_on_429:
                return None  # signal to retry
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.error("ER request failed for '%s': %s", area, e)
            return []

        articles = data.get("articles", {}).get("results", [])
        events: list[RawEvent] = []
        for art in articles:
            url = art.get("url", "")
            title = art.get("title", "")
            body = art.get("body", "")
            if not url or not title:
                continue
            event = self._make_event(
                title=title,
                content=body or title,
                url=url,
                published_at=self._parse_date(art.get("dateTime", "")),
                raw_metadata={
                    "source_title": art.get("source", {}).get("title", ""),
                    "sentiment": art.get("sentiment", None),
                    "categories": [c.get("label", "") for c in art.get("categories", [])],
                    "area": area,
                },
            )
            if event is not None:
                events.append(event)
        return events

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
