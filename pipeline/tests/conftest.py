"""Shared fixtures for OpenClaw pipeline tests."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openclaw.models import RawEvent, ScoredEvent, ApprovedItem, ClaimTriplet, FactCheckResult


@pytest.fixture
def make_raw_event():
    """Factory for RawEvent with sensible defaults."""
    def _make(
        title="Test headline",
        content="Test content body",
        url="https://example.com/article",
        source_collector="rss",
        published_at=None,
        raw_metadata=None,
    ):
        return RawEvent(
            source_collector=source_collector,
            title=title,
            content=content,
            url=url,
            published_at=published_at or datetime.utcnow(),
            raw_metadata=raw_metadata or {},
        )
    return _make


@pytest.fixture
def make_scored_event(make_raw_event):
    """Factory for ScoredEvent."""
    def _make(area="tech", score=0.5, priority="P2", **kwargs):
        raw = make_raw_event(**kwargs)
        return ScoredEvent(raw_event=raw, area=area, score=score, priority=priority)
    return _make
