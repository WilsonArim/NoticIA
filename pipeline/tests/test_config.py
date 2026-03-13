"""Test pipeline configuration completeness."""
from openclaw.config import (
    GDELT_QUERIES, BREAKING_SIGNALS, QUEUE_CAPS,
    SEEN_HASHES_CAP, SEEN_TITLES_CAP, TITLE_SIMILARITY_THRESHOLD,
    MAX_PER_AREA_IN_FLUSH, AI_HEURISTIC_PHRASES,
    COLLECTOR_INTERVALS, PIPELINE_INTERVALS,
    EDITOR_TEMPERATURES, XAI_PRICING,
)
from openclaw.reporters.base import REPORTER_CONFIGS


def test_14_gdelt_queries():
    assert len(GDELT_QUERIES) == 14
    for area, query in GDELT_QUERIES.items():
        assert isinstance(query, str) and len(query) > 5, f"Empty query for {area}"


def test_14_reporter_configs():
    assert len(REPORTER_CONFIGS) == 14
    expected_areas = {
        "geopolitics", "defense", "economy", "tech", "energy", "health",
        "environment", "crypto", "regulation", "portugal", "science",
        "financial_markets", "society", "sports",
    }
    assert set(REPORTER_CONFIGS.keys()) == expected_areas


def test_reporter_configs_have_keywords():
    for area, config in REPORTER_CONFIGS.items():
        assert config.weighted_keywords, f"Reporter '{area}' has no keywords"
        assert config.threshold > 0, f"Reporter '{area}' has zero threshold"


def test_breaking_signals_populated():
    assert len(BREAKING_SIGNALS) >= 10


def test_queue_caps():
    assert QUEUE_CAPS == {"P1": 10, "P2": 25, "P3": 30}


def test_memory_caps():
    assert SEEN_HASHES_CAP == 10_000
    assert SEEN_TITLES_CAP == 10_000


def test_title_similarity_threshold():
    assert 0.0 < TITLE_SIMILARITY_THRESHOLD < 1.0


def test_collector_intervals():
    assert len(COLLECTOR_INTERVALS) == 6
    assert COLLECTOR_INTERVALS["gdelt"] == 15
    assert COLLECTOR_INTERVALS["telegram"] == 5


def test_pipeline_intervals():
    assert PIPELINE_INTERVALS["P1"] == 30
    assert PIPELINE_INTERVALS["P2"] == 180
    assert PIPELINE_INTERVALS["P3"] == 720


def test_ai_heuristic_phrases():
    assert len(AI_HEURISTIC_PHRASES) >= 10
    for phrase in AI_HEURISTIC_PHRASES:
        assert phrase == phrase.lower(), f"Phrase not lowercase: {phrase}"
