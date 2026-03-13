"""Stage 4: Relation Extraction — Grok S-A-O triples."""
from __future__ import annotations

import json
import logging

from openclaw.editorial.grok_client import GrokClient
from openclaw.editorial.token_tracker import TokenTracker
from openclaw.models import ClaimTriplet

logger = logging.getLogger("openclaw.factcheck.relations")

EXTRACTION_PROMPT = """Extract Subject-Action-Object triples from each claim.
Return a JSON array of objects with: claim, subject, action, object.

Example:
Input: "Russia imposed sanctions on Lithuanian exports"
Output: [{"claim": "Russia imposed sanctions on Lithuanian exports", "subject": "Russia", "action": "imposed sanctions on", "object": "Lithuanian exports"}]

Return ONLY the JSON array."""


class RelationExtractor:
    """Extract S-A-O triples from claims using Grok. Fix Bug #4: store triples."""

    def __init__(self, grok: GrokClient, tracker: TokenTracker) -> None:
        self.grok = grok
        self.tracker = tracker

    async def extract(self, claims: list[str]) -> list[ClaimTriplet]:
        """Extract triples from a list of claims."""
        if not claims:
            return []

        user_content = "Claims:\n" + "\n".join(f"- {c}" for c in claims)

        try:
            response, usage = await self.grok.chat(
                system_prompt=EXTRACTION_PROMPT,
                user_content=user_content,
                temperature=0.1,
                max_tokens=2048,
            )
            usage.call_name = "relation_extraction"
            self.tracker.track(usage)

            return self._parse_triples(response)
        except Exception as e:
            logger.error("Relation extraction failed: %s", e)
            return []

    @staticmethod
    def _parse_triples(response: str) -> list[ClaimTriplet]:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]

            data = json.loads(text.strip())
            return [
                ClaimTriplet(
                    claim=d.get("claim", ""),
                    subject=d.get("subject", ""),
                    action=d.get("action", ""),
                    object=d.get("object", ""),
                )
                for d in data
            ]
        except (json.JSONDecodeError, TypeError):
            return []
