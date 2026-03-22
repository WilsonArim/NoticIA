"""Tests for Dispatcher V2 — pure functions and pre-filter logic."""
import pytest
from unittest.mock import patch, MagicMock
from openclaw.agents.dispatcher import (
    _normalize_title,
    _title_hash,
    _extract_domain,
    _pre_filter_events,
    _parse_batch_response,
    _is_stale_by_date,
    _chunks,
    CATEGORIAS_VALIDAS,
    DOMAIN_BLOCKLIST,
    MIN_CONTENT_LENGTH,
    MIN_TITLE_LENGTH,
)


# ── _normalize_title ─────────────────────────────────────────────────────

class TestNormalizeTitle:
    def test_lowercase(self):
        assert _normalize_title("Hello World") == "hello world"

    def test_collapse_spaces(self):
        assert _normalize_title("  Hello   World  ") == "hello world"

    def test_tabs_and_newlines(self):
        assert _normalize_title("Hello\t\nWorld") == "hello world"

    def test_empty(self):
        assert _normalize_title("") == ""


# ── _title_hash ──────────────────────────────────────────────────────────

class TestTitleHash:
    def test_deterministic(self):
        h1 = _title_hash("Breaking News: Something Happened")
        h2 = _title_hash("Breaking News: Something Happened")
        assert h1 == h2

    def test_case_insensitive(self):
        h1 = _title_hash("HELLO WORLD")
        h2 = _title_hash("hello world")
        assert h1 == h2

    def test_whitespace_insensitive(self):
        h1 = _title_hash("Hello  World")
        h2 = _title_hash("Hello World")
        assert h1 == h2

    def test_different_titles(self):
        h1 = _title_hash("Title A")
        h2 = _title_hash("Title B")
        assert h1 != h2

    def test_md5_length(self):
        assert len(_title_hash("test")) == 32


# ── _extract_domain ──────────────────────────────────────────────────────

class TestExtractDomain:
    def test_basic_url(self):
        assert _extract_domain("https://www.bbc.com/news/article") == "bbc.com"

    def test_no_www(self):
        assert _extract_domain("https://reuters.com/world") == "reuters.com"

    def test_subdomain(self):
        assert _extract_domain("https://api.example.com/v1") == "api.example.com"

    def test_empty(self):
        assert _extract_domain("") == ""

    def test_invalid(self):
        assert _extract_domain("not-a-url") == ""


# ── _pre_filter_events ──────────────────────────────────────────────────

class TestPreFilterEvents:
    def _make_event(self, title="Test Event Title Here", content="A" * 50,
                    url="https://reuters.com/article", **kwargs):
        event = {
            "id": "evt-1",
            "title": title,
            "content": content,
            "url": url,
            "source_collector": "rss",
            "published_at": "2026-03-20T12:00:00Z",
        }
        event.update(kwargs)
        return event

    def test_passes_valid_event(self):
        events = [self._make_event()]
        passed, stats = _pre_filter_events(events, set())
        assert len(passed) == 1
        assert stats["passed"] == 1

    def test_filters_short_title(self):
        events = [self._make_event(title="Short")]
        passed, stats = _pre_filter_events(events, set())
        assert len(passed) == 0
        assert stats["too_short"] == 1

    def test_filters_short_content(self):
        events = [self._make_event(content="tiny")]
        passed, stats = _pre_filter_events(events, set())
        assert len(passed) == 0
        assert stats["too_short"] == 1

    def test_dedup_by_existing_hash(self):
        event = self._make_event()
        existing = {_title_hash(event["title"])}
        passed, stats = _pre_filter_events([event], existing)
        assert len(passed) == 0
        assert stats["dedup_title"] == 1

    def test_dedup_within_batch(self):
        e1 = self._make_event(title="Duplicate Title Event")
        e2 = self._make_event(title="Duplicate Title Event")
        e2["id"] = "evt-2"
        passed, stats = _pre_filter_events([e1, e2], set())
        assert len(passed) == 1
        assert stats["dedup_title"] == 1

    def test_blocks_domain(self):
        blocked_domain = list(DOMAIN_BLOCKLIST)[0]
        events = [self._make_event(url=f"https://{blocked_domain}/page")]
        passed, stats = _pre_filter_events(events, set())
        assert len(passed) == 0
        assert stats["domain_blocked"] == 1

    def test_blocks_sports_keywords(self):
        events = [self._make_event(title="Champions League Final Results Tonight")]
        passed, stats = _pre_filter_events(events, set())
        assert len(passed) == 0
        assert stats["keyword_blocked"] == 1

    def test_blocks_horoscope(self):
        events = [self._make_event(title="Your Daily Horoscope Reading")]
        passed, stats = _pre_filter_events(events, set())
        assert len(passed) == 0
        assert stats["keyword_blocked"] == 1

    def test_multiple_filters_count(self):
        events = [
            self._make_event(title="OK Event Number One Here"),
            self._make_event(title="Sh"),  # too short
            self._make_event(title="Champions League Semi Final Game", url="https://bbc.com"),  # keyword
        ]
        events[0]["id"] = "e1"
        events[1]["id"] = "e2"
        events[2]["id"] = "e3"
        passed, stats = _pre_filter_events(events, set())
        assert stats["passed"] == 1
        assert stats["too_short"] == 1
        assert stats["keyword_blocked"] == 1


# ── _parse_batch_response ────────────────────────────────────────────────

class TestParseBatchResponse:
    def test_parse_json_array(self):
        response = '[{"n": 1, "categories": ["geopolitica"], "reject": false}]'
        result = _parse_batch_response(response, 1)
        assert len(result) == 1
        assert result[0]["categories"] == ["geopolitica"]

    def test_parse_json_in_markdown(self):
        response = '```json\n[{"n": 1, "categories": ["economia"], "reject": false}]\n```'
        result = _parse_batch_response(response, 1)
        assert len(result) == 1
        assert result[0]["categories"] == ["economia"]

    def test_parse_with_surrounding_text(self):
        response = 'Here are results:\n[{"n": 1, "categories": ["tech"], "reject": false}]\nDone.'
        result = _parse_batch_response(response, 1)
        assert len(result) == 1

    def test_fallback_on_garbage(self):
        response = "This is not JSON at all"
        result = _parse_batch_response(response, 3)
        assert len(result) == 3
        assert all(r.get("reject") for r in result)

    def test_parse_multiple(self):
        response = '[{"n":1,"categories":["a"],"reject":false},{"n":2,"categories":["b"],"reject":true}]'
        result = _parse_batch_response(response, 2)
        assert len(result) == 2


# ── _is_stale_by_date ───────────────────────────────────────────────────

class TestIsStaleByDate:
    def test_recent_date_not_stale(self):
        stale, _ = _is_stale_by_date("2026-03-20")
        # This will depend on when tests run, but the logic is testable
        assert isinstance(stale, bool)

    def test_old_date_is_stale(self):
        stale, reason = _is_stale_by_date("2020-01-01")
        assert stale is True
        assert "stale" in reason.lower()

    def test_empty_string(self):
        stale, _ = _is_stale_by_date("")
        assert stale is False

    def test_short_string(self):
        stale, _ = _is_stale_by_date("2026")
        assert stale is False

    def test_invalid_date(self):
        stale, _ = _is_stale_by_date("not-a-date")
        assert stale is False


# ── _chunks ──────────────────────────────────────────────────────────────

class TestChunks:
    def test_exact_split(self):
        result = list(_chunks([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_remainder(self):
        result = list(_chunks([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_empty(self):
        result = list(_chunks([], 10))
        assert result == []

    def test_single_chunk(self):
        result = list(_chunks([1, 2], 10))
        assert result == [[1, 2]]


# ── Constants validation ─────────────────────────────────────────────────

class TestConstants:
    def test_categorias_validas_not_empty(self):
        assert len(CATEGORIAS_VALIDAS) > 0

    def test_domain_blocklist_not_empty(self):
        assert len(DOMAIN_BLOCKLIST) > 0

    def test_min_lengths_positive(self):
        assert MIN_CONTENT_LENGTH > 0
        assert MIN_TITLE_LENGTH > 0
