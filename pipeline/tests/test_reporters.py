"""Parametrized tests across ALL 14 areas for reporters."""
import pytest
from datetime import datetime
from openclaw.reporters.base import score_event, classify_priority, REPORTER_CONFIGS, create_all_reporters
from openclaw.models import RawEvent


def _make_event(title="Test", content="", source_collector="rss", published_at=None, **meta):
    return RawEvent(
        source_collector=source_collector,
        title=title, content=content,
        url=f"https://test.com/{title[:20]}",
        published_at=published_at or datetime.utcnow(),
        raw_metadata=meta,
    )


ALL_AREAS = list(REPORTER_CONFIGS.keys())


# Get the top keyword (weight=5) for each area
def _top_keyword(area):
    config = REPORTER_CONFIGS[area]
    for weight in sorted(config.weighted_keywords.keys(), reverse=True):
        terms = config.weighted_keywords[weight]
        if terms:
            return terms[0]
    return ""


@pytest.mark.parametrize("area", ALL_AREAS)
def test_score_nonzero_for_matched_keyword(area):
    keyword = _top_keyword(area)
    event = _make_event(title=keyword, content=f"Details about {keyword}")
    config = REPORTER_CONFIGS[area]
    score = score_event(event, config)
    assert score > 0, f"Area '{area}' keyword '{keyword}' should score > 0"


@pytest.mark.parametrize("area", ALL_AREAS)
def test_score_zero_for_unrelated(area):
    event = _make_event(title="Cat sat on mat", content="Fluffy was lazy.")
    config = REPORTER_CONFIGS[area]
    score = score_event(event, config)
    assert score == 0.0, f"Area '{area}' should score 0 for unrelated content"


def test_breaking_signal_forces_p1():
    event = _make_event(title="BREAKING: earthquake hits", content="Major earthquake")
    priority = classify_priority(0.1, event, 0.30)
    assert priority == "P1"


def test_classify_priority_thresholds():
    event = _make_event(title="Normal article", content="Nothing special")
    assert classify_priority(0.80, event, 0.30) == "P1"
    assert classify_priority(0.50, event, 0.30) == "P2"
    assert classify_priority(0.35, event, 0.30) == "P3"
    assert classify_priority(0.10, event, 0.30) == ""


def test_is_breaking_metadata_forces_p1():
    event = _make_event(title="Normal", content="Content", is_breaking=True)
    priority = classify_priority(0.1, event, 0.30)
    assert priority == "P1"


def test_empty_title_scores_zero():
    event = _make_event(title="", content="")
    config = REPORTER_CONFIGS["tech"]
    assert score_event(event, config) == 0.0


def test_long_content_no_crash():
    event = _make_event(title="Test", content="a " * 5000)
    config = REPORTER_CONFIGS["tech"]
    score_event(event, config)  # Should not crash


def test_create_all_reporters():
    reporters = create_all_reporters()
    assert len(reporters) == 14
