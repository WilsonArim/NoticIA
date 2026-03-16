"""ACLED Conflict Data Collector — daily, OAuth authentication."""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from openclaw.collectors.base import BaseCollector
from openclaw.config import ACLED_EMAIL, ACLED_PASSWORD
from openclaw.models import RawEvent

ACLED_TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_API_URL = "https://acleddata.com/api/acled/read"


class ACLEDCollector(BaseCollector):
    """Collects armed conflict event data from ACLED via OAuth."""

    name = "acled"
    requires_api_key = True

    def __init__(self) -> None:
        super().__init__()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: float = 0.0

    async def _authenticate(self) -> bool:
        """Obtain OAuth access token using email + password."""
        if not ACLED_EMAIL or not ACLED_PASSWORD:
            self.logger.warning("ACLED credentials not configured, skipping")
            return False

        client = await self.get_client()
        try:
            resp = await client.post(
                ACLED_TOKEN_URL,
                data={
                    "username": ACLED_EMAIL,
                    "password": ACLED_PASSWORD,
                    "grant_type": "password",
                    "client_id": "acled",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.error("ACLED OAuth authentication failed: %s", e)
            return False

        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        expires_in = int(data.get("expires_in", 86400))
        # Renew 5 minutes before expiry
        self._token_expires_at = time.time() + expires_in - 300

        if not self._access_token:
            self.logger.error("ACLED OAuth returned no access_token")
            return False

        self.logger.info("ACLED OAuth authenticated (expires in %ds)", expires_in)
        return True

    async def _refresh_access_token(self) -> bool:
        """Use refresh token to get a new access token."""
        if not self._refresh_token:
            return await self._authenticate()

        client = await self.get_client()
        try:
            resp = await client.post(
                ACLED_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": "acled",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.warning("ACLED token refresh failed, re-authenticating: %s", e)
            return await self._authenticate()

        self._access_token = data.get("access_token")
        new_refresh = data.get("refresh_token")
        if new_refresh:
            self._refresh_token = new_refresh
        expires_in = int(data.get("expires_in", 86400))
        self._token_expires_at = time.time() + expires_in - 300

        self.logger.info("ACLED token refreshed (expires in %ds)", expires_in)
        return bool(self._access_token)

    async def _ensure_token(self) -> bool:
        """Ensure we have a valid access token."""
        if self._access_token and time.time() < self._token_expires_at:
            return True
        if self._refresh_token:
            return await self._refresh_access_token()
        return await self._authenticate()

    async def collect(self) -> list[RawEvent]:
        if not await self._ensure_token():
            return []

        client = await self.get_client()
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        params = {
            "limit": 100,
            "event_date": yesterday,
            "event_date_where": ">=",
            "_format": "json",
        }
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            resp = await client.get(ACLED_API_URL, params=params, headers=headers)

            # If 401, try refreshing token and retry once
            if resp.status_code == 401:
                self.logger.warning("ACLED 401, refreshing token...")
                if await self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self._access_token}"}
                    resp = await client.get(
                        ACLED_API_URL, params=params, headers=headers
                    )

            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.error("ACLED request failed: %s", e)
            return []

        records = data.get("data", [])
        events: list[RawEvent] = []
        for rec in records:
            title = (
                rec.get("event_type", "Unknown")
                + ": "
                + rec.get("notes", "")[:120]
            )
            fatalities = int(rec.get("fatalities", 0))
            event = self._make_event(
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
            )
            if event is not None:
                events.append(event)
        self.logger.info("ACLED collected %d conflict events", len(events))
        return events

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, AttributeError):
            return None
