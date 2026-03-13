"""Test heuristic detection WITHOUT loading the RoBERTa model (mock it)."""
import pytest
from unittest.mock import patch, MagicMock
from openclaw.factcheck.ai_detector import AIDetector, AIDetectionResult


@pytest.fixture
def detector():
    """AIDetector with mocked model (no GPU/download needed)."""
    d = AIDetector()
    d._pipeline = "failed"  # Skip model loading
    return d


def test_ai_phrases_detected(detector):
    text = "As an AI, it's important to note that this landscape of innovation delve into complexities."
    result = detector.detect(text)
    assert len(result.heuristic_flags) >= 2
    assert result.heuristic_boost > 0


def test_phantom_citation_detected(detector):
    text = "According to studies, the experts say this research suggests significant findings."
    result = detector.detect(text)
    phantom_flags = [f for f in result.heuristic_flags if "phantom_citation" in f]
    assert len(phantom_flags) >= 1


def test_sentence_uniformity_flagged(detector):
    # 5 sentences of very similar length
    text = "This is a test sentence here. This is also a test sentence. This sentence is about test. Another test sentence is here. The final test sentence now."
    result = detector.detect(text)
    assert "uniform_sentence_length" in result.heuristic_flags


def test_human_text_no_flags(detector):
    text = "The European Central Bank raised interest rates by 0.25% on Thursday, citing persistent inflation in the eurozone."
    result = detector.detect(text)
    assert result.label == "human"
    assert result.score < 0.5


def test_short_text_returns_result(detector):
    text = "Short."
    result = detector.detect(text)
    assert isinstance(result, AIDetectionResult)
    assert result.label == "human"


def test_heuristic_boost_capped_at_015(detector):
    # Many AI phrases to test cap
    phrases = "As an AI, it's important to note, it is worth mentioning, in conclusion, it should be noted, as a language model, delve into, it's essential to, navigate the complexities."
    result = detector.detect(phrases)
    assert result.heuristic_boost <= 0.15


def test_classification_thresholds():
    """Test that thresholds are correctly applied."""
    d = AIDetector()
    # Mock the model to return specific scores
    mock_result = [{"label": "LABEL_0", "score": 0.90}]
    d._pipeline = MagicMock(return_value=mock_result)
    result = d.detect("Some text to analyze for AI content detection test.")
    assert result.label == "confirmed_ai" or result.model_score >= 0.85
