"""Base collector abstract class."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

import httpx

from openclaw.models import RawEvent

MAX_EVENT_AGE_HOURS = 72  # Reject events older than 72 hours


class BaseCollector(ABC):
    """Abstract base for all collectors."""

    name: str = "base"
    requires_api_key: bool = False

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"openclaw.collector.{self.name}")
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @abstractmethod
    async def collect(self) -> list[RawEvent]:
        """Collect raw events from this source."""
        ...

    def _make_event(
        self,
        title: str,
        content: str,
        url: str,
        published_at: datetime | None = None,
        raw_metadata: dict[str, Any] | None = None,
    ) -> RawEvent | None:
        if published_at is None:
            self.logger.debug("Event sem published_at, rejeitado: %s", title[:80])
            return None

        age = datetime.utcnow() - published_at
        if age > timedelta(hours=MAX_EVENT_AGE_HOURS):
            self.logger.debug(
                "Event demasiado velho (%.1fh): %s",
                age.total_seconds() / 3600,
                title[:80],
            )
            return None

        return RawEvent(
            source_collector=self.name,
            title=title,
            content=content,
            url=url,
            published_at=published_at,
            raw_metadata=raw_metadata or {},
        )
