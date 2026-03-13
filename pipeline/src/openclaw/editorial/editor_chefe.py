"""Editor-Chefe — LLM-powered editorial decision maker."""
from __future__ import annotations

import json
import logging

from openclaw.config import EDITOR_TEMPERATURES
from openclaw.editorial.grok_client import GrokClient
from openclaw.editorial.prompt_cache import get_editor_system_prompt
from openclaw.editorial.token_tracker import TokenTracker
from openclaw.models import ApprovedItem, ScoredEvent

logger = logging.getLogger("openclaw.editorial.editor")


class EditorChefe:
    """Editor-Chefe: 1 LLM call per batch, returns approved items."""

    def __init__(self) -> None:
        self.grok = GrokClient()
        self.token_tracker = TokenTracker()

    async def evaluate_batch(
        self, events: list[ScoredEvent], priority: str
    ) -> list[ApprovedItem]:
        """Evaluate a batch of events. 1 LLM call per batch."""
        if not events:
            return []

        system_prompt = get_editor_system_prompt(priority)
        temperature = EDITOR_TEMPERATURES.get(priority, 0.3)

        # Build user content
        user_content = self._format_batch(events)

        try:
            response_text, token_usage = await self.grok.chat(
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=temperature,
            )
            token_usage.call_name = f"editor_chefe_{priority}"
            token_usage.priority = priority
            self.token_tracker.track(token_usage)

            approved = self._parse_response(response_text)
            logger.info(
                "Editor-Chefe %s: %d/%d events approved (cost: $%.4f)",
                priority, len(approved), len(events), token_usage.cost_usd,
            )
            return approved

        except Exception as e:
            logger.error("Editor-Chefe batch evaluation failed: %s", e)
            return []

    async def close(self) -> None:
        await self.token_tracker.flush()
        await self.grok.close()

    def _format_batch(self, events: list[ScoredEvent]) -> str:
        """Format events for the LLM prompt."""
        items = []
        for i, ev in enumerate(events, 1):
            items.append(
                f"--- Event {i} ---\n"
                f"ID: {ev.raw_event.id}\n"
                f"Title: {ev.raw_event.title}\n"
                f"Content: {ev.raw_event.content[:500]}\n"
                f"Area: {ev.area}\n"
                f"Score: {ev.score:.2f}\n"
                f"Source: {ev.raw_event.url}\n"
                f"Collector: {ev.raw_event.source_collector}\n"
                f"Keywords: {', '.join(ev.matched_keywords[:10])}\n"
            )
        return "\n".join(items)

    @staticmethod
    def _parse_response(response_text: str) -> list[ApprovedItem]:
        """Parse Grok JSON response into ApprovedItems."""
        try:
            # Strip markdown code fences if present
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            if not isinstance(data, list):
                data = [data]

            items = []
            for d in data:
                items.append(ApprovedItem(
                    id=d.get("id", ""),
                    area=d.get("area", ""),
                    priority=d.get("priority", "P3"),
                    urgency_score=float(d.get("urgency_score", 0.5)),
                    headline=d.get("headline", ""),
                    summary=d.get("summary", ""),
                    claims=d.get("claims", []),
                    justification=d.get("justification", ""),
                    source_url=d.get("source_url", ""),
                    source_title=d.get("source_title", ""),
                ))
            return items
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Failed to parse Editor-Chefe response: %s", e)
            return []
