"""Stage 6: Auditor 'O Cetico' — final consistency audit."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from openclaw.editorial.grok_client import GrokClient
from openclaw.editorial.token_tracker import TokenTracker

logger = logging.getLogger("openclaw.factcheck.auditor")


def _build_auditor_prompt() -> str:
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""Current real date: {current_date}.
Your knowledge cutoff is November 2024. For events after that date, rely on the evidence provided — do NOT dismiss claims as "future" or "unverifiable" simply because they are from 2025-2026.

You are "O Cetico" (The Skeptic) — a rigorous fact-check auditor.
Review ALL accumulated evidence and give a final verdict.

Evidence will include: AI detection results, source checks, multi-source verification, relation triples.

Your verdicts:
- "consistente" — Evidence is consistent, claims appear reliable
- "retry" — Insufficient evidence, recommend re-running multi-source verification
- "irreconciliavel" — Irreconcilable contradictions, reject this item

Return ONLY a JSON object: {{"verdict": "...", "reasoning": "...", "confidence": 0.0-1.0}}"""


@dataclass
class AuditResult:
    verdict: str  # consistente, retry, irreconciliavel
    reasoning: str = ""
    confidence: float = 0.5


class Auditor:
    """'O Cetico' — final audit with auto-rejection rules."""

    def __init__(self, grok: GrokClient, tracker: TokenTracker) -> None:
        self.grok = grok
        self.tracker = tracker

    async def audit(self, evidence: dict) -> AuditResult:
        """Audit accumulated evidence. Auto-reject before LLM if clear-cut."""
        # Auto-rejection rules (no LLM needed)
        ai_verdict = evidence.get("ai_detection", {}).get("label", "")
        if ai_verdict == "confirmed_ai":
            return AuditResult(verdict="irreconciliavel", reasoning="AI-generated content confirmed", confidence=0.95)

        phantom_flags = evidence.get("phantom_sources", [])
        flagged_sources = [s for s in phantom_flags if s.get("flags")]
        if len(flagged_sources) >= 2:
            return AuditResult(verdict="irreconciliavel", reasoning=f"{len(flagged_sources)} phantom sources detected", confidence=0.9)

        invalid_dois = [s for s in phantom_flags if "invalid_doi" in s.get("flags", [])]
        if invalid_dois:
            return AuditResult(verdict="irreconciliavel", reasoning="Invalid DOI detected", confidence=0.85)

        # LLM audit for non-obvious cases
        try:
            evidence_text = json.dumps(evidence, indent=2, default=str)[:3000]
            response, usage = await self.grok.chat(
                system_prompt=_build_auditor_prompt(),
                user_content=f"Evidence:\n{evidence_text}",
                temperature=0.1,
                max_tokens=1024,
            )
            usage.call_name = "auditor_o_cetico"
            self.tracker.track(usage)

            return self._parse_verdict(response)
        except Exception as e:
            logger.error("Auditor LLM call failed: %s", e)
            return AuditResult(verdict="retry", reasoning=f"Audit error: {e}", confidence=0.3)

    @staticmethod
    def _parse_verdict(response: str) -> AuditResult:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return AuditResult(
                verdict=data.get("verdict", "retry"),
                reasoning=data.get("reasoning", ""),
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, TypeError):
            return AuditResult(verdict="retry", reasoning="Failed to parse audit response")
