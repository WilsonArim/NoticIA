"""Tests for Escritor — slugify, staleness check."""
import pytest
from openclaw.agents.escritor import (
    _slugify,
    _event_is_stale,
)


# ── _slugify ─────────────────────────────────────────────────────────────

class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_accents(self):
        assert _slugify("Café Résumé") == "cafe-resume"

    def test_portuguese_chars(self):
        assert _slugify("Ação do Governo Português") == "acao-do-governo-portugues"

    def test_special_chars_removed(self):
        assert _slugify("Hello! World? #Test") == "hello-world-test"

    def test_max_length(self):
        long_title = "A" * 200
        result = _slugify(long_title)
        assert len(result) <= 80

    def test_multiple_spaces(self):
        assert _slugify("Hello   World   Test") == "hello-world-test"

    def test_leading_trailing_spaces(self):
        assert _slugify("  Hello World  ") == "hello-world"

    def test_empty(self):
        assert _slugify("") == ""

    def test_cedilla(self):
        assert _slugify("França") == "franca"

    def test_tilde_n(self):
        assert _slugify("España") == "espana"

    def test_mixed_accents(self):
        slug = _slugify("Notícia sobre União Europeia")
        assert "noticia" in slug
        assert "uniao" in slug
        assert "europeia" in slug


# ── _event_is_stale ─────────────────────────────────────────────────────

class TestEventIsStale:
    def test_old_date_stale(self):
        assert _event_is_stale("2020-01-01") is True

    def test_none_not_stale(self):
        assert _event_is_stale(None) is False

    def test_empty_not_stale(self):
        assert _event_is_stale("") is False

    def test_short_string_not_stale(self):
        assert _event_is_stale("2026") is False

    def test_invalid_not_stale(self):
        assert _event_is_stale("invalid-date") is False
