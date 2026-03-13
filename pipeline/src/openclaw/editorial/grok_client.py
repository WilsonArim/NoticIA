"""Grok LLM Client with circuit breaker and retry logic."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from openclaw.config import (
    CIRCUIT_BREAKER_PAUSE_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
    RETRY_BACKOFF_BASE,
    RETRY_MAX,
    XAI_API_KEY,
    XAI_BASE_URL,
    XAI_MODEL,
    XAI_PRICING,
)
from openclaw.models import TokenUsage

logger = logging.getLogger("openclaw.editorial.grok")


@dataclass
class GrokClient:
    """Async Grok client with circuit breaker and retry."""

    _consecutive_failures: int = 0
    _circuit_open_until: float = 0.0
    _client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _is_circuit_open(self) -> bool:
        if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            if time.time() < self._circuit_open_until:
                return True
            # Reset after pause
            self._consecutive_failures = 0
        return False

    async def chat(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> tuple[str, TokenUsage]:
        """Send a chat completion request to Grok. Returns (response_text, token_usage)."""
        if self._is_circuit_open():
            logger.warning("Circuit breaker OPEN — skipping Grok call")
            raise RuntimeError("Circuit breaker open")

        if not XAI_API_KEY:
            raise RuntimeError("XAI_API_KEY not configured")

        client = await self.get_client()
        payload = {
            "model": XAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(RETRY_MAX):
            try:
                resp = await client.post(
                    f"{XAI_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract response
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                cached_tokens = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
                cost = (
                    (input_tokens / 1_000_000) * XAI_PRICING["input_per_m"]
                    + (output_tokens / 1_000_000) * XAI_PRICING["output_per_m"]
                )

                self._consecutive_failures = 0
                return content, TokenUsage(
                    call_name="grok_chat",
                    model=XAI_MODEL,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    cost_usd=cost,
                )

            except Exception as e:
                last_error = e
                self._consecutive_failures += 1
                if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                    self._circuit_open_until = time.time() + CIRCUIT_BREAKER_PAUSE_SECONDS
                    logger.error("Circuit breaker TRIGGERED after %d failures", CIRCUIT_BREAKER_THRESHOLD)
                    break
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.warning("Grok call failed (attempt %d/%d), retrying in %ds: %s", attempt + 1, RETRY_MAX, wait, e)
                await asyncio.sleep(wait)

        raise RuntimeError(f"Grok call failed after {RETRY_MAX} retries: {last_error}")
