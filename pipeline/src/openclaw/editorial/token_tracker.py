"""Token usage tracker for FinOps."""
from __future__ import annotations

import logging

import httpx

from openclaw.config import PUBLISH_API_KEY, SUPABASE_SERVICE_KEY, SUPABASE_URL
from openclaw.models import TokenUsage

logger = logging.getLogger("openclaw.editorial.tokens")


class TokenTracker:
    """Tracks and persists token usage to Supabase token_logs table."""

    def __init__(self) -> None:
        self._buffer: list[TokenUsage] = []

    def track(self, usage: TokenUsage) -> None:
        self._buffer.append(usage)
        logger.debug(
            "Token usage: %s | in=%d out=%d cost=$%.4f",
            usage.call_name, usage.input_tokens, usage.output_tokens, usage.cost_usd,
        )

    async def flush(self) -> None:
        """Persist buffered token usage to Supabase."""
        if not self._buffer:
            return

        records = [
            {
                "call_name": u.call_name,
                "model": u.model,
                "priority": u.priority or None,
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "cached_tokens": u.cached_tokens,
                "cost_usd": u.cost_usd,
            }
            for u in self._buffer
        ]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SUPABASE_URL}/rest/v1/token_logs",
                    json=records,
                    headers={
                        "apikey": SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                )
                resp.raise_for_status()
                logger.info("Flushed %d token logs to Supabase", len(records))
                self._buffer.clear()
        except Exception as e:
            logger.error("Failed to flush token logs: %s", e)
