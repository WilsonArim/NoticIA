"""Test FactChecker._final_scoring() directly."""
import pytest
from unittest.mock import MagicMock
from openclaw.factcheck.checker import FactChecker


class MockAuditResult:
    def __init__(self, verdict):
        self.verdict = verdict
        self.reasoning = "test reasoning"


class MockVerification:
    def __init__(self, verdict, weighted_score=1.0):
        self.verdict = verdict
        self.claim = "test claim"
        self.weighted_score = weighted_score


def _make_result(ai_label="human", ai_score=0.1):
    r = MagicMock()
    r.ai_detection = {"label": ai_label, "score": ai_score}
    return r


def test_ai_generated_verdict():
    result = _make_result(ai_label="confirmed_ai", ai_score=0.95)
    audit = MockAuditResult("aprovado")
    verifications = [MockVerification("cross_reference")]
    verdict, conf = FactChecker._final_scoring(result, audit, verifications)
    assert verdict == "ai_generated"


def test_irreconciliavel_verdict():
    result = _make_result()
    audit = MockAuditResult("irreconciliavel")
    verifications = [MockVerification("cross_reference")]
    verdict, conf = FactChecker._final_scoring(result, audit, verifications)
    assert verdict == "disputed"
    assert conf < 0.5  # Heavy penalty


def test_confirmed_verdict():
    result = _make_result()
    audit = MockAuditResult("aprovado")
    verifications = [MockVerification("cross_reference"), MockVerification("cross_reference")]
    verdict, conf = FactChecker._final_scoring(result, audit, verifications)
    assert verdict == "confirmed"


def test_unverifiable_verdict():
    result = _make_result()
    audit = MockAuditResult("aprovado")
    verifications = [MockVerification("none"), MockVerification("none")]
    verdict, conf = FactChecker._final_scoring(result, audit, verifications)
    assert verdict == "unverifiable"


def test_empty_verifications():
    result = _make_result()
    audit = MockAuditResult("aprovado")
    verdict, conf = FactChecker._final_scoring(result, audit, [])
    assert verdict == "unverifiable"


def test_confidence_clamped():
    result = _make_result(ai_score=0.0)
    audit = MockAuditResult("aprovado")
    verifications = [MockVerification("cross_reference")]
    _, conf = FactChecker._final_scoring(result, audit, verifications)
    assert 0.0 <= conf <= 1.0


def test_max_penalties():
    result = _make_result(ai_score=1.0)
    audit = MockAuditResult("irreconciliavel")
    verifications = [MockVerification("none")]
    _, conf = FactChecker._final_scoring(result, audit, verifications)
    assert 0.0 <= conf <= 1.0
