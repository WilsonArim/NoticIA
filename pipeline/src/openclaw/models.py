"""Core data models for the OpenClaw pipeline."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawEvent:
    """Output of collectors — a single raw news event."""
    source_collector: str  # gdelt, acled, x, rss, telegram, event_registry, crawl4ai
    title: str
    content: str
    url: str
    published_at: datetime
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.url}:{self.source_collector}".encode()
            ).hexdigest()


@dataclass
class ScoredEvent:
    """Output of reporters — a scored and classified event."""
    raw_event: RawEvent
    area: str
    score: float
    matched_keywords: list[str] = field(default_factory=list)
    priority: str = "P3"  # P1, P2, P3
    verification_hints: list[str] = field(default_factory=list)


@dataclass
class ApprovedItem:
    """Output of Editor-Chefe — an editorially approved item."""
    id: str
    area: str
    priority: str
    urgency_score: float
    headline: str
    summary: str
    claims: list[str] = field(default_factory=list)
    justification: str = ""
    source_url: str = ""
    source_title: str = ""


@dataclass
class ClaimTriplet:
    """Subject-Action-Object triple extracted from a claim."""
    claim: str
    subject: str
    action: str
    object: str


@dataclass
class FactCheckResult:
    """Output of the 7-stage fact-check pipeline."""
    item_id: str
    verdict: str  # confirmed, disputed, unverifiable, ai_generated
    confidence_score: float
    ai_detection: dict[str, Any] = field(default_factory=dict)
    phantom_sources: list[dict[str, Any]] = field(default_factory=list)
    embeddings_stored: bool = False
    triplets: list[ClaimTriplet] = field(default_factory=list)
    multi_source: dict[str, Any] = field(default_factory=dict)
    auditor_verdict: str = ""
    rationale_chain: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SourceCredibility:
    """Credibility tier for a news source domain."""
    domain: str
    name: str
    tier: int  # 1-6
    weight: float  # 1.0 to 0.0
    bias_flags: list[str] = field(default_factory=list)
    category: str = ""


@dataclass
class TokenUsage:
    """FinOps tracking for a single LLM call."""
    call_name: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    priority: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PipelineMetrics:
    """Aggregated metrics for a pipeline run."""
    stage: str
    events_in: int = 0
    events_out: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)
