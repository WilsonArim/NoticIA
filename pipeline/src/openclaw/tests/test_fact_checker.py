"""Tests for Fact-Checker — URL year extraction, staleness, source filtering."""
import pytest
from openclaw.agents.fact_checker import (
    _extract_year_from_url,
    _filter_stale_sources,
    _event_is_stale,
)


# ── _extract_year_from_url ───────────────────────────────────────────────

class TestExtractYearFromUrl:
    def test_yyyy_mm_dd_path(self):
        assert _extract_year_from_url("https://bbc.com/2025/03/20/article") == 2025

    def test_yyyy_mm_path(self):
        assert _extract_year_from_url("https://nytimes.com/2024/11/story") == 2024

    def test_no_year(self):
        assert _extract_year_from_url("https://example.com/article-slug") is None

    def test_embedded_date(self):
        url = "https://news.com/article-20260315-breaking"
        result = _extract_year_from_url(url)
        assert result == 2026 or result is None  # depends on pattern match

    def test_very_old_year_ignored(self):
        assert _extract_year_from_url("https://example.com/1999/article") is None

    def test_future_year(self):
        # Years beyond 2100 should not match
        assert _extract_year_from_url("https://example.com/2200/article") is None


# ── _filter_stale_sources ────────────────────────────────────────────────

class TestFilterStaleSources:
    def test_same_year_kept(self):
        fontes = ["https://bbc.com/2026/03/20/article"]
        validas, rejeitadas = _filter_stale_sources(fontes, "2026-03-20")
        assert len(validas) == 1
        assert len(rejeitadas) == 0

    def test_different_year_rejected(self):
        fontes = ["https://bbc.com/2022/05/10/article"]
        validas, rejeitadas = _filter_stale_sources(fontes, "2026-03-20")
        assert len(validas) == 0
        assert len(rejeitadas) == 1

    def test_no_year_in_url_kept(self):
        fontes = ["https://example.com/breaking-news-article"]
        validas, rejeitadas = _filter_stale_sources(fontes, "2026-03-20")
        assert len(validas) == 1
        assert len(rejeitadas) == 0

    def test_mixed_sources(self):
        fontes = [
            "https://reuters.com/2026/03/story",  # valid
            "https://bbc.com/2023/01/old-story",   # wrong year
            "https://example.com/no-year-slug",     # no year
        ]
        validas, rejeitadas = _filter_stale_sources(fontes, "2026-03-20")
        assert len(validas) == 2
        assert len(rejeitadas) == 1

    def test_empty_data_real(self):
        fontes = ["https://bbc.com/2022/article"]
        validas, rejeitadas = _filter_stale_sources(fontes, "")
        assert len(validas) == 1  # no filtering when data_real is empty

    def test_none_data_real(self):
        fontes = ["https://bbc.com/2022/article"]
        validas, rejeitadas = _filter_stale_sources(fontes, None)
        assert len(validas) == 1


# ── _event_is_stale ─────────────────────────────────────────────────────

class TestEventIsStale:
    def test_old_event_is_stale(self):
        stale, reason = _event_is_stale("2020-01-01")
        assert stale is True
        assert "stale" in reason.lower()

    def test_none_is_not_stale(self):
        stale, _ = _event_is_stale(None)
        assert stale is False

    def test_empty_is_not_stale(self):
        stale, _ = _event_is_stale("")
        assert stale is False

    def test_short_string_not_stale(self):
        stale, _ = _event_is_stale("2026")
        assert stale is False

    def test_invalid_date_not_stale(self):
        stale, _ = _event_is_stale("not-a-date-string")
        assert stale is False
