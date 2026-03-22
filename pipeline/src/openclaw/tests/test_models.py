"""Tests for core data models."""
import pytest
from openclaw.models import RawEvent, TokenUsage, PipelineMetrics
from datetime import datetime


class TestRawEvent:
    def test_auto_id_generation(self):
        event = RawEvent(
            source_collector="rss",
            title="Test",
            content="Content",
            url="https://example.com/article",
            published_at=datetime(2026, 3, 20),
        )
        assert event.id != ""
        assert len(event.id) == 64  # sha256 hex length

    def test_deterministic_id(self):
        kwargs = dict(
            source_collector="rss",
            title="Test",
            content="Content",
            url="https://example.com/article",
            published_at=datetime(2026, 3, 20),
        )
        e1 = RawEvent(**kwargs)
        e2 = RawEvent(**kwargs)
        assert e1.id == e2.id

    def test_different_url_different_id(self):
        base = dict(
            source_collector="rss",
            title="Test",
            content="Content",
            published_at=datetime(2026, 3, 20),
        )
        e1 = RawEvent(url="https://a.com/1", **base)
        e2 = RawEvent(url="https://b.com/2", **base)
        assert e1.id != e2.id

    def test_different_collector_different_id(self):
        base = dict(
            title="Test",
            content="Content",
            url="https://example.com",
            published_at=datetime(2026, 3, 20),
        )
        e1 = RawEvent(source_collector="rss", **base)
        e2 = RawEvent(source_collector="gdelt", **base)
        assert e1.id != e2.id

    def test_custom_id_preserved(self):
        event = RawEvent(
            id="custom-id",
            source_collector="rss",
            title="Test",
            content="Content",
            url="https://example.com",
            published_at=datetime(2026, 3, 20),
        )
        assert event.id == "custom-id"


class TestTokenUsage:
    def test_defaults(self):
        usage = TokenUsage(call_name="test", model="gpt-4")
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cost_usd == 0.0


class TestPipelineMetrics:
    def test_defaults(self):
        metrics = PipelineMetrics(stage="dispatcher")
        assert metrics.events_in == 0
        assert metrics.events_out == 0
        assert metrics.errors == []
