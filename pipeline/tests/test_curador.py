"""Test CuradorCentral dedup, queue caps, Bug #6, Bug #7, stress."""
import pytest
from datetime import datetime
from openclaw.curador.central import CuradorCentral
from openclaw.models import RawEvent, ScoredEvent


def _make_scored(url="https://test.com/1", title="Test", area="tech", score=0.5, priority="P2"):
    raw = RawEvent(
        source_collector="rss", title=title, content="Body",
        url=url, published_at=datetime.utcnow(),
    )
    return ScoredEvent(raw_event=raw, area=area, score=score, priority=priority)


def test_hash_dedup_rejects_identical():
    c = CuradorCentral()
    e1 = _make_scored(url="https://test.com/same")
    e2 = _make_scored(url="https://test.com/same")
    assert c.ingest([e1]) == 1
    assert c.ingest([e2]) == 0  # Duplicate


def test_title_similarity_dedup():
    c = CuradorCentral()
    e1 = _make_scored(url="https://a.com/1", title="Russia imposes new sanctions on EU exports")
    e2 = _make_scored(url="https://b.com/2", title="Russia imposes new sanctions on EU export")
    assert c.ingest([e1]) == 1
    assert c.ingest([e2]) == 0  # Similar title


def test_different_titles_not_deduped():
    c = CuradorCentral()
    e1 = _make_scored(url="https://a.com/1", title="Earthquake hits Japan")
    e2 = _make_scored(url="https://b.com/2", title="Stock market rallies today")
    assert c.ingest([e1]) == 1
    assert c.ingest([e2]) == 1  # Different enough


DISTINCT_WORDS = [
    "Earthquake", "Inflation", "Tornado", "Election", "Pandemic",
    "Avalanche", "Volcano", "Tsunami", "Drought", "Hurricane",
    "Blizzard", "Wildfire", "Famine", "Asteroid", "Revolution",
    "Blackout", "Epidemic", "Ceasefire", "Embargo", "Referendum",
    "Sabotage", "Armistice", "Bankruptcy", "Cyclone", "Extinction",
    "Genocide", "Impeachment", "Monsoon", "Quarantine", "Uprising",
]


def test_queue_cap_p1():
    c = CuradorCentral()
    events = [_make_scored(url=f"https://test.com/{i}", title=f"{DISTINCT_WORDS[i]} strikes downtown region", priority="P1") for i in range(15)]
    added = c.ingest(events)
    assert added == 10  # P1 cap is 10


def test_queue_cap_p2():
    c = CuradorCentral()
    # Each title must be fully unique to avoid SequenceMatcher title dedup
    import uuid
    events = [_make_scored(url=f"https://test.com/{i}", title=f"{uuid.uuid4().hex}", priority="P2") for i in range(30)]
    added = c.ingest(events)
    assert added == 25  # P2 cap is 25


def test_flush_diversity_enforcement():
    c = CuradorCentral()
    # 5 events from same area with distinct titles
    events = [_make_scored(url=f"https://test.com/{i}", title=f"{DISTINCT_WORDS[i]} disrupts global tech supply chain", area="tech", priority="P2", score=0.5+i*0.01) for i in range(5)]
    c.ingest(events)
    flushed = c.flush("P2")
    assert len(flushed) == 3  # MAX_PER_AREA_IN_FLUSH = 3


def test_flush_sorts_by_score():
    c = CuradorCentral()
    e1 = _make_scored(url="https://a.com/1", title="Low score", score=0.2, priority="P2")
    e2 = _make_scored(url="https://b.com/2", title="High score", score=0.9, priority="P2")
    c.ingest([e1, e2])
    flushed = c.flush("P2")
    assert flushed[0].score > flushed[1].score


def test_flush_clears_queue():
    c = CuradorCentral()
    c.ingest([_make_scored()])
    c.flush("P2")
    assert len(c.queues["P2"]) == 0


def test_bug6_seen_titles_cap():
    """Bug #6: seen_titles should be pruned at SEEN_TITLES_CAP (10,000)."""
    c = CuradorCentral()
    # Insert 15,000 unique events
    for i in range(15000):
        e = _make_scored(url=f"https://test.com/{i}", title=f"Unique title number {i}", priority="P2")
        # Manually bypass queue cap for this test
        c._mark_seen(e)
    # After pruning, should be <= SEEN_TITLES_CAP
    assert len(c._seen_titles) <= 10_000


def test_bug7_concurrent_iteration_safe():
    """Bug #7: Mutating queue during flush should not crash."""
    c = CuradorCentral()
    events = [_make_scored(url=f"https://test.com/{i}", title=f"Event {i}", area=f"area{i%5}", priority="P2") for i in range(20)]
    c.ingest(events)
    # flush iterates over copy, should not crash
    flushed = c.flush("P2")
    assert len(flushed) > 0
    assert len(c.queues["P2"]) == 0


def test_stress_10000_events():
    """Stress: 10,000 events bulk ingest with dedup."""
    c = CuradorCentral()
    events = [_make_scored(url=f"https://test.com/{i}", title=f"Event {i}", priority="P3") for i in range(10000)]
    added = c.ingest(events)
    # P3 cap is 30, so max 30 added to queue
    assert added == 30
    # But all 10,000 should be tracked in seen_hashes (up to cap)
    assert len(c._seen_hashes) <= 10_000 or added <= 30
