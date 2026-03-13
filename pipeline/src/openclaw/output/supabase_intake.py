"""Publisher — sends approved items to Supabase via Edge Functions."""
from __future__ import annotations

import logging
import uuid

import httpx

from openclaw.config import (
    EDGE_AGENT_LOG,
    EDGE_RECEIVE_ARTICLE,
    EDGE_RECEIVE_CLAIMS,
    EDGE_RECEIVE_RATIONALE,
    PUBLISH_API_KEY,
    SUPABASE_SERVICE_KEY,
    SUPABASE_URL,
)
from openclaw.models import ApprovedItem, ClaimTriplet, FactCheckResult

logger = logging.getLogger("openclaw.output.publisher")

# Area name mapping: pipeline internal → DB enum
AREA_MAP = {
    "geopolitics": "Geopolitica",
    "defense": "Defesa",
    "economy": "Economia",
    "tech": "Tech",
    "energy": "Energia",
    "health": "Saude",
    "environment": "Ambiente",
    "crypto": "Crypto",
    "regulation": "Regulacao",
    "portugal": "Portugal",
    "science": "Ciencia",
    "financial_markets": "Mercados",
    "society": "Sociedade",
    "sports": "Desporto",
}


class SupabasePublisher:
    """Publishes verified items to Supabase via Edge Functions and REST API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def publish(self, item: ApprovedItem, fact_check: FactCheckResult) -> bool:
        """Publish an approved + fact-checked item. Returns True if successful."""
        # Rejection rules
        if fact_check.verdict == "ai_generated":
            logger.info("REJECTED (ai_generated): %s", item.headline[:60])
            await self._log_rejection(item, fact_check, "ai_generated")
            return False

        if fact_check.auditor_verdict == "irreconciliavel":
            logger.info("REJECTED (irreconciliavel): %s", item.headline[:60])
            await self._log_rejection(item, fact_check, "irreconciliavel")
            return False

        # Insert into intake_queue via REST API
        client = await self.get_client()
        try:
            intake_data = {
                "source_event_id": item.id,
                "title": item.headline,
                "content": item.summary,
                "url": item.source_url,
                "area": AREA_MAP.get(item.area, item.area),
                "score": item.urgency_score,
                "claims": self._format_claims(item.claims, fact_check.triplets),
                "sources": [{"url": item.source_url, "title": item.source_title}],
                "rationale": fact_check.rationale_chain,
                "fact_check_summary": {
                    "verdict": fact_check.verdict,
                    "confidence": fact_check.confidence_score,
                    "ai_detection": fact_check.ai_detection,
                    "auditor_verdict": fact_check.auditor_verdict,
                },
                "priority": item.priority.lower(),
                "status": "pending",
            }
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/intake_queue",
                json=intake_data,
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
            )
            resp.raise_for_status()
            logger.info("Published to intake_queue: %s [%s]", item.headline[:60], fact_check.verdict)

            # Fix Bug #4: Store structured triplets in claims table
            await self._store_triplets(client, item, fact_check.triplets)

            # Log agent event
            await self._log_agent_event(item, fact_check)
            return True

        except Exception as e:
            logger.error("Failed to publish to Supabase: %s", e)
            return False

    @staticmethod
    def _format_claims(claims: list[str], triplets: list[ClaimTriplet]) -> list[dict]:
        """Format claims with S-A-O triplet data for intake_queue JSONB field."""
        triplet_map = {t.claim: t for t in triplets} if triplets else {}
        result = []
        for claim_text in claims:
            entry: dict = {"original_text": claim_text}
            triplet = triplet_map.get(claim_text)
            if triplet:
                entry["subject"] = triplet.subject
                entry["predicate"] = triplet.action
                entry["object"] = triplet.object
            result.append(entry)
        return result

    async def _store_triplets(
        self, client: httpx.AsyncClient, item: ApprovedItem, triplets: list[ClaimTriplet]
    ) -> None:
        """Fix Bug #4: Store structured S-A-O triplets via receive-claims Edge Function.

        Uses the existing Edge Function which handles claims table insertion
        and article_claims junction linking. Field names match the Edge Function
        schema: original_text (not claim_text), subject, predicate, object.
        """
        if not triplets:
            return

        claims_payload = [
            {
                "original_text": triplet.claim,
                "subject": triplet.subject,
                "predicate": triplet.action,
                "object": triplet.object,
            }
            for triplet in triplets
        ]

        try:
            resp = await client.post(
                EDGE_RECEIVE_CLAIMS,
                json={
                    "article_id": item.id,
                    "claims": claims_payload,
                },
                headers={
                    "Authorization": f"Bearer {PUBLISH_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            logger.info("Stored %d triplets for item %s via Edge Function", len(triplets), item.id[:8])
        except Exception as e:
            logger.warning("Failed to store triplets for item %s: %s", item.id[:8], e)

    async def _log_rejection(self, item: ApprovedItem, fc: FactCheckResult, reason: str) -> None:
        """Log a rejection event."""
        try:
            client = await self.get_client()
            await client.post(
                EDGE_AGENT_LOG,
                json=[{
                    "agent_name": "publisher",
                    "run_id": str(uuid.uuid4()),
                    "event_type": "skipped",
                    "payload": {"item_id": item.id, "reason": reason, "headline": item.headline[:100]},
                }],
                headers={
                    "Authorization": f"Bearer {PUBLISH_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
        except Exception as e:
            logger.warning("Failed to log rejection: %s", e)

    async def _log_agent_event(self, item: ApprovedItem, fc: FactCheckResult) -> None:
        """Log a successful publish event."""
        try:
            client = await self.get_client()
            await client.post(
                EDGE_AGENT_LOG,
                json=[{
                    "agent_name": "publisher",
                    "run_id": str(uuid.uuid4()),
                    "event_type": "completed",
                    "payload": {
                        "item_id": item.id,
                        "verdict": fc.verdict,
                        "confidence": fc.confidence_score,
                        "headline": item.headline[:100],
                    },
                }],
                headers={
                    "Authorization": f"Bearer {PUBLISH_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
        except Exception as e:
            logger.warning("Failed to log publish event: %s", e)
