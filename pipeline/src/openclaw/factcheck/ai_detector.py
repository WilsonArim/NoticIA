"""Stage 1: AI Content Detector — RoBERTa local + heuristics."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from openclaw.config import (
    AI_DETECTION_CONFIRMED_THRESHOLD,
    AI_DETECTION_SUSPECTED_THRESHOLD,
    AI_HEURISTIC_PHRASES,
)

logger = logging.getLogger("openclaw.factcheck.ai_detector")


@dataclass
class AIDetectionResult:
    score: float
    label: str  # confirmed_ai, suspected_ai, human
    heuristic_flags: list[str]
    model_score: float
    heuristic_boost: float


class AIDetector:
    """Detect AI-generated content using RoBERTa + heuristics."""

    def __init__(self) -> None:
        self._pipeline = None

    def _load_model(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline(
                    "text-classification",
                    model="roberta-base-openai-detector",
                    device=-1,  # CPU
                )
                logger.info("RoBERTa AI detector loaded")
            except Exception as e:
                logger.error("Failed to load AI detector model: %s", e)
                self._pipeline = "failed"

    def detect(self, text: str) -> AIDetectionResult:
        """Detect if text is AI-generated. Fix Bug #1: analyze ORIGINAL content, not Grok summary."""
        self._load_model()

        # Model score
        model_score = 0.0
        if self._pipeline and self._pipeline != "failed":
            try:
                # Truncate to model's max length
                result = self._pipeline(text[:512])
                for r in result:
                    if r["label"] == "LABEL_0":  # Fake/AI
                        model_score = r["score"]
            except Exception as e:
                logger.warning("AI detection model error: %s", e)

        # Heuristic flags
        text_lower = text.lower()
        flags = [phrase for phrase in AI_HEURISTIC_PHRASES if phrase in text_lower]

        # Phantom citations
        phantom_patterns = [
            r"according to (?:studies|experts|research)",
            r"research (?:shows|suggests|indicates)",
            r"experts (?:say|believe|agree)",
        ]
        for pattern in phantom_patterns:
            if re.search(pattern, text_lower):
                flags.append(f"phantom_citation: {pattern}")

        # Sentence uniformity check
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if len(sentences) >= 5:
            lengths = [len(s) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            if mean_len > 0:
                variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
                cv = (variance ** 0.5) / mean_len
                if cv < 0.25:
                    flags.append("uniform_sentence_length")

        # Heuristic boost
        heuristic_boost = min(len(flags) * 0.03, 0.15)
        final_score = min(model_score + heuristic_boost, 1.0)

        # Classify
        if final_score >= AI_DETECTION_CONFIRMED_THRESHOLD:
            label = "confirmed_ai"
        elif final_score >= AI_DETECTION_SUSPECTED_THRESHOLD:
            label = "suspected_ai"
        else:
            label = "human"

        return AIDetectionResult(
            score=final_score,
            label=label,
            heuristic_flags=flags,
            model_score=model_score,
            heuristic_boost=heuristic_boost,
        )
