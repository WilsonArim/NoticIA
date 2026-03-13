"""Curador Central — Dedup, priority queues, diversity enforcement."""
from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from openclaw.config import (
    MAX_PER_AREA_IN_FLUSH,
    QUEUE_CAPS,
    SEEN_HASHES_CAP,
    SEEN_TITLES_CAP,
    TITLE_SIMILARITY_THRESHOLD,
)
from openclaw.models import ScoredEvent

logger = logging.getLogger("openclaw.curador")


@dataclass
class CuradorCentral:
    """Central curation: dedup, classify, queue, flush."""

    queues: dict[str, list[ScoredEvent]] = field(default_factory=lambda: {
        "P1": [], "P2": [], "P3": [],
    })
    _seen_hashes: set[str] = field(default_factory=set)
    _seen_titles: list[str] = field(default_factory=list)

    def ingest(self, events: list[ScoredEvent]) -> int:
        """Ingest scored events into priority queues. Returns count added."""
        added = 0
        for event in events:
            if self._is_duplicate(event):
                continue
            queue = event.priority
            if queue not in self.queues:
                continue
            if len(self.queues[queue]) >= QUEUE_CAPS.get(queue, 30):
                logger.warning("Queue %s full (%d), discarding event", queue, QUEUE_CAPS[queue])
                continue
            self.queues[queue].append(event)
            self._mark_seen(event)
            added += 1
        return added

    def flush(self, priority: str) -> list[ScoredEvent]:
        """Flush a priority queue with diversity enforcement."""
        if priority not in self.queues:
            return []

        queue = self.queues[priority]
        if not queue:
            return []

        # Sort by score descending
        queue.sort(key=lambda e: e.score, reverse=True)

        # Diversity: max N events per area
        area_counts: dict[str, int] = defaultdict(int)
        flushed: list[ScoredEvent] = []

        # Fix Bug #7: iterate over a copy to avoid mutation during iteration
        for event in list(queue):
            if area_counts[event.area] >= MAX_PER_AREA_IN_FLUSH:
                continue
            flushed.append(event)
            area_counts[event.area] += 1

        # Clear the queue
        self.queues[priority] = []

        logger.info(
            "Flushed %d events from %s queue (diversity enforced: %s)",
            len(flushed), priority, dict(area_counts),
        )
        return flushed

    def _is_duplicate(self, event: ScoredEvent) -> bool:
        """2-layer dedup: hash (exact) + title similarity."""
        # Layer 1: Hash (same URL + same collector)
        event_hash = hashlib.sha256(
            f"{event.raw_event.url}:{event.raw_event.source_collector}".encode()
        ).hexdigest()
        if event_hash in self._seen_hashes:
            return True

        # Layer 2: Title similarity (SequenceMatcher >= 0.85)
        title_lower = event.raw_event.title.lower()
        for seen_title in self._seen_titles:
            ratio = SequenceMatcher(None, title_lower, seen_title).ratio()
            if ratio >= TITLE_SIMILARITY_THRESHOLD:
                return True

        return False

    def _mark_seen(self, event: ScoredEvent) -> None:
        """Track seen events with memory caps."""
        event_hash = hashlib.sha256(
            f"{event.raw_event.url}:{event.raw_event.source_collector}".encode()
        ).hexdigest()
        self._seen_hashes.add(event_hash)
        self._seen_titles.append(event.raw_event.title.lower())

        # Fix Bug #6: Cap memory to prevent leaks
        if len(self._seen_hashes) > SEEN_HASHES_CAP:
            # Remove oldest half
            hashes_list = list(self._seen_hashes)
            self._seen_hashes = set(hashes_list[SEEN_HASHES_CAP // 2:])
            logger.info("Pruned seen_hashes to %d", len(self._seen_hashes))

        if len(self._seen_titles) > SEEN_TITLES_CAP:
            self._seen_titles = self._seen_titles[SEEN_TITLES_CAP // 2:]
            logger.info("Pruned seen_titles to %d", len(self._seen_titles))
