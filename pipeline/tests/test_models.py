"""Test ALL 8 dataclasses in openclaw.models."""
import pytest
from datetime import datetime
from openclaw.models import (
    RawEvent, ScoredEvent, ApprovedItem, ClaimTriplet,
    FactCheckResult, TokenUsage, PipelineMetrics,
)


class TestRawEvent:
    def test_auto_generates_sha256_id(self):
        event = RawEvent(
            source_collector="rss",
            title="Test",
            content="Body",
            url="https://example.com/article",
            published_at=datetime.utcnow(),
        )
        assert event.id is not None
        assert len(event.id) == 64  # SHA256 hex digest

    def test_deterministic_id_same_url_collector(self):
        kwargs = dict(
            source_collector="rss",
            title="Test",
            content="Body",
            url="https://example.com/same",
            published_at=datetime.utcnow(),
        )
        e1 = RawEvent(**kwargs)
        e2 = RawEvent(**kwargs)
        assert e1.id == e2.id

    def test_different_url_produces_different_id(self):
        base = dict(
            source_collector="rss",
            title="Test",
            content="Body",
            published_at=datetime.utcnow(),
        )
        e1 = RawEvent(url="https://example.com/a", **base)
        e2 = RawEvent(url="https://example.com/b", **base)
        assert e1.id != e2.id

    def test_custom_id_preserved(self):
        event = RawEvent(
            id="custom-id-123",
            source_collector="rss",
            title="Test",
            content="Body",
            url="https://example.com/article",
            published_at=datetime.utcnow(),
        )
        assert event.id == "custom-id-123"


class TestScoredEvent:
    def test_defaults(self, make_raw_event):
        raw = make_raw_event()
        scored = ScoredEvent(raw_event=raw, area="tech", score=0.5)
        assert scored.priority == "P3"

    def test_all_fields(self, make_raw_event):
        raw = make_raw_event()
        scored = ScoredEvent(raw_event=raw, area="economy", score=0.8, priority="P1")
        assert scored.area == "economy"
        assert scored.score == 0.8
        assert scored.priority == "P1"


class TestApprovedItem:
    def test_all_fields(self):
        approved = ApprovedItem(
            id="test-123",
            area="tech",
            priority="P2",
            urgency_score=0.6,
            headline="Test Headline",
            summary="Test Summary",
            claims=["Claim 1", "Claim 2"],
        )
        assert len(approved.claims) == 2
        assert approved.area == "tech"
        assert approved.headline == "Test Headline"


class TestClaimTriplet:
    def test_all_fields(self):
        triplet = ClaimTriplet(
            claim="Russia imposed sanctions",
            subject="Russia",
            action="imposed sanctions on",
            object="EU",
        )
        assert triplet.subject == "Russia"
        assert triplet.action == "imposed sanctions on"
        assert triplet.object == "EU"


class TestFactCheckResult:
    def test_defaults(self):
        result = FactCheckResult(
            item_id="test-123",
            verdict="unverifiable",
            confidence_score=0.5,
        )
        assert result.verdict == "unverifiable"
        assert result.confidence_score >= 0.0
        assert isinstance(result.phantom_sources, list)
        assert isinstance(result.triplets, list)


class TestTokenUsage:
    def test_timestamp_auto_set(self):
        usage = TokenUsage(
            call_name="test_call",
            model="grok-3",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.01,
        )
        assert usage.timestamp is not None
        assert isinstance(usage.timestamp, datetime)


class TestPipelineMetrics:
    def test_defaults(self):
        metrics = PipelineMetrics(stage="collect")
        assert metrics.events_in == 0
        assert metrics.events_out == 0
        assert metrics.total_cost_usd == 0.0
