"""ACLED Conflict Data Collector — daily, requires API key."""
from __future__ import annotations

from datetime import datetime, timedelta

from openclaw.collectors.base import BaseCollector
from openclaw.config import ACLED_API_KEY, ACLED_EMAIL
from openclaw.models import RawEvent

ACLED_API_URL = "https://api.acleddata.com/acled/read"


class ACLEDCollector(BaseCollector):
    """Collects armed conflict event data from ACLED."""

    name = "acled"
    requires_api_key = True

    async def collect(self) -> list[RawEvent]:
        if not ACLED_API_KEY or not ACLED_EMAIL:
            self.logger.warning("ACLED credentials not configured, skipping")
            return []
        client = await self.get_client()
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        params = {
            "key": ACLED_API_KEY,
            "email": ACLED_EMAIL,
            "limit": 100,
            "event_date": yesterday,
            "event_date_where": ">=",
        }
        try:
            resp = await client.get(ACLED_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.error("ACLED request failed: %s", e)
            return []

        records = data.get("data", [])
        events: list[RawEvent] = []
        for rec in records:
            title = rec.get("event_type", "Unknown") + ": " + rec.get("notes", "")[:120]
            fatalities = int(rec.get("fatalities", 0))
            events.append(self._make_event(
                title=title,
                content=rec.get("notes", title),
                url=f"https://acleddata.com/data/{rec.get('event_id_cnty', '')}",
                published_at=self._parse_date(rec.get("event_date", "")),
                raw_metadata={
                    "event_type": rec.get("event_type", ""),
                    "sub_event_type": rec.get("sub_event_type", ""),
                    "country": rec.get("country", ""),
                    "region": rec.get("region", ""),
                    "fatalities": fatalities,
                    "actor1": rec.get("actor1", ""),
                    "actor2": rec.get("actor2", ""),
                    "latitude": rec.get("latitude", ""),
                    "longitude": rec.get("longitude", ""),
                    "is_breaking": fatalities > 0,
                },
            ))
        self.logger.info("ACLED collected %d conflict events", len(events))
        return events

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, AttributeError):
            return datetime.utcnow()
