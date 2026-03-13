"""Fact-Check Orchestrator — runs all 7 stages sequentially."""
from __future__ import annotations

import logging

from openclaw.editorial.grok_client import GrokClient
from openclaw.editorial.token_tracker import TokenTracker
from openclaw.factcheck.ai_detector import AIDetector
from openclaw.factcheck.auditor import Auditor
from openclaw.factcheck.local_embeddings import LocalEmbeddings
from openclaw.factcheck.multi_source import MultiSourceVerifier
from openclaw.factcheck.phantom_source import PhantomSourceDetector
from openclaw.factcheck.relation_extractor import RelationExtractor
from openclaw.models import ApprovedItem, FactCheckResult

logger = logging.getLogger("openclaw.factcheck.checker")


class FactChecker:
    """Orchestrates the 7-stage fact-check pipeline for each ApprovedItem."""

    def __init__(self) -> None:
        self.ai_detector = AIDetector()
        self.phantom_detector = PhantomSourceDetector()
        self.embeddings = LocalEmbeddings()
        self.grok = GrokClient()
        self.tracker = TokenTracker()
        self.relation_extractor = RelationExtractor(self.grok, self.tracker)
        self.multi_source = MultiSourceVerifier()
        self.auditor = Auditor(self.grok, self.tracker)

    async def check(self, item: ApprovedItem, original_content: str = "") -> FactCheckResult:
        """Run all 7 stages on a single ApprovedItem."""
        result = FactCheckResult(item_id=item.id)
        rationale: list[dict] = []

        # Stage 1: AI Detection — Fix Bug #1: use ORIGINAL content, not Grok summary
        content_to_check = original_content if original_content else item.summary
        ai_result = self.ai_detector.detect(content_to_check)
        result.ai_detection = {
            "score": ai_result.score,
            "label": ai_result.label,
            "heuristic_flags": ai_result.heuristic_flags,
        }
        rationale.append({"stage": "ai_detector", "result": result.ai_detection})

        if ai_result.label == "confirmed_ai":
            result.verdict = "ai_generated"
            result.confidence_score = 1.0 - ai_result.score
            result.rationale_chain = rationale
            logger.info("Item %s REJECTED: AI-generated (score=%.2f)", item.id[:8], ai_result.score)
            return result

        # Stage 2: Phantom Source Detection
        source_results = await self.phantom_detector.check_sources(item.summary, [item.source_url] if item.source_url else None)
        result.phantom_sources = [
            {"url": s.url, "reachable": s.reachable, "flags": s.flags}
            for s in source_results
        ]
        rationale.append({"stage": "phantom_source", "result": result.phantom_sources})

        # Stage 3: Multi-HyDE Embeddings — Fix Bug #3: generate AND store in pgvector
        embedding_results = self.embeddings.generate_embeddings(item.claims)
        await self.embeddings.store_embeddings(embedding_results)
        result.embeddings_stored = any(r.stored for r in embedding_results)
        rationale.append({"stage": "multi_hyde", "stored": result.embeddings_stored})

        # Stage 4: Relation Extraction — Fix Bug #4: store triples
        triplets = await self.relation_extractor.extract(item.claims)
        result.triplets = triplets
        rationale.append({
            "stage": "relation_extractor",
            "triplets": [{"s": t.subject, "a": t.action, "o": t.object} for t in triplets],
        })

        # Stage 5: Multi-Source Verification — Fix Bug #5: validate content
        verification_results = await self.multi_source.verify_claims(item.claims)
        result.multi_source = {
            "results": [
                {"claim": v.claim, "verdict": v.verdict, "score": v.weighted_score}
                for v in verification_results
            ]
        }
        rationale.append({"stage": "multi_source", "result": result.multi_source})

        # Stage 6: Auditor "O Cetico"
        evidence = {
            "ai_detection": result.ai_detection,
            "phantom_sources": result.phantom_sources,
            "multi_source": result.multi_source,
            "triplets_count": len(triplets),
        }
        audit_result = await self.auditor.audit(evidence)
        result.auditor_verdict = audit_result.verdict
        rationale.append({
            "stage": "auditor",
            "verdict": audit_result.verdict,
            "reasoning": audit_result.reasoning,
        })

        # Stage 7: Scoring Final
        result.verdict, result.confidence_score = self._final_scoring(result, audit_result, verification_results)
        rationale.append({
            "stage": "scoring_final",
            "verdict": result.verdict,
            "confidence": result.confidence_score,
        })

        result.rationale_chain = rationale
        logger.info(
            "Item %s: verdict=%s confidence=%.2f",
            item.id[:8], result.verdict, result.confidence_score,
        )
        return result

    async def close(self) -> None:
        await self.tracker.flush()
        await self.grok.close()
        await self.embeddings.close()

    @staticmethod
    def _final_scoring(result, audit_result, verification_results) -> tuple[str, float]:
        """Stage 7: Calculate final verdict and confidence score."""
        # Verdict determination
        if result.ai_detection.get("label") == "confirmed_ai":
            verdict = "ai_generated"
        elif audit_result.verdict == "irreconciliavel":
            verdict = "disputed"
        elif verification_results and all(v.verdict == "cross_reference" for v in verification_results):
            verdict = "confirmed"
        elif not verification_results or all(v.verdict == "none" for v in verification_results):
            verdict = "unverifiable"
        else:
            verdict = "disputed"

        # Confidence score calculation
        base = 1.0
        ai_score = result.ai_detection.get("score", 0.0)
        base -= ai_score * 0.3

        sourced_count = sum(1 for v in verification_results if v.verdict != "none")
        total = max(len(verification_results), 1)
        sourced_ratio = sourced_count / total
        base *= (0.5 + 0.5 * sourced_ratio)

        if audit_result.verdict == "irreconciliavel":
            base *= 0.2
        elif audit_result.verdict == "retry":
            base *= 0.5

        confidence = max(0.0, min(1.0, base))
        return verdict, confidence
