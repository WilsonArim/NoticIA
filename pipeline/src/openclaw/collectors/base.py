"""Base collector abstract class."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx

from openclaw.models import RawEvent


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
    ) -> RawEvent:
        return RawEvent(
            source_collector=self.name,
            title=title,
            content=content,
            url=url,
            published_at=published_at or datetime.utcnow(),
            raw_metadata=raw_metadata or {},
        )
