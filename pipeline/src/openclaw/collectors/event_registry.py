"""Event Registry API Collector — 14 queries, requires API key."""
from __future__ import annotations

import asyncio
from datetime import datetime

from openclaw.collectors.base import BaseCollector
from openclaw.config import EVENT_REGISTRY_API_KEY, GDELT_QUERIES
from openclaw.models import RawEvent

ER_API_URL = "https://eventregistry.org/api/v1/article/getArticles"


class EventRegistryCollector(BaseCollector):
    """Collects articles from Event Registry API."""

    name = "event_registry"
    requires_api_key = True

    async def collect(self) -> list[RawEvent]:
        if not EVENT_REGISTRY_API_KEY:
            self.logger.warning("Event Registry API key not configured, skipping")
            return []
        client = await self.get_client()
        tasks = [
            self._query_area(client, area, query)
            for area, query in GDELT_QUERIES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        events: list[RawEvent] = []
        for area, result in zip(GDELT_QUERIES.keys(), results):
            if isinstance(result, Exception):
                self.logger.warning("ER query '%s' failed: %s", area, result)
                continue
            events.extend(result)
        self.logger.info("Event Registry collected %d events", len(events))
        return events

    async def _query_area(self, client, area: str, query: str) -> list[RawEvent]:
        payload = {
            "keyword": query,
            "lang": "eng",
            "articlesCount": 50,
            "articlesSortBy": "date",
            "apiKey": EVENT_REGISTRY_API_KEY,
        }
        try:
            resp = await client.post(ER_API_URL, json=payload)
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
            events.append(self._make_event(
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
            ))
        return events

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.utcnow()
