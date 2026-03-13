"""Pipeline Runner — APScheduler orchestration for collectors and pipeline stages."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from openclaw.collectors import create_all_collectors
from openclaw.collectors.crawl4ai_collector import Crawl4AICollector
from openclaw.config import COLLECTOR_INTERVALS, PIPELINE_INTERVALS
from openclaw.curador.central import CuradorCentral
from openclaw.editorial.editor_chefe import EditorChefe
from openclaw.factcheck.checker import FactChecker
from openclaw.models import RawEvent, ScoredEvent
from openclaw.output.supabase_intake import SupabasePublisher
from openclaw.reporters.base import create_all_reporters

logger = logging.getLogger("openclaw.scheduler")

# Global state
_mesa_comum: list[RawEvent] = []
_curador = CuradorCentral()
_editor = EditorChefe()
_fact_checker = FactChecker()
_publisher = SupabasePublisher()
_enricher = Crawl4AICollector()


async def collect_job(collector_name: str) -> None:
    """Run a single collector and add events to mesa comum."""
    global _mesa_comum
    collectors = create_all_collectors()
    collector = next((c for c in collectors if c.name == collector_name), None)
    if not collector:
        logger.warning("Collector '%s' not found", collector_name)
        return

    try:
        events = await collector.collect()

        # Enrich GDELT events with Crawl4AI (Fix Bug #2)
        if collector_name == "gdelt":
            enriched = []
            for event in events:
                if event.raw_metadata.get("needs_enrichment"):
                    event = await _enricher.enrich_event(event)
                enriched.append(event)
            events = enriched

        # Score with all reporters
        reporters = create_all_reporters()
        scored: list[ScoredEvent] = []
        for reporter in reporters:
            scored.extend(reporter.score_events(events))

        # Ingest into curador
        added = _curador.ingest(scored)
        logger.info("Collector '%s': %d events → %d scored → %d queued", collector_name, len(events), len(scored), added)
        await collector.close()
    except Exception as e:
        logger.error("Collector '%s' job failed: %s", collector_name, e, exc_info=True)


async def pipeline_job(priority: str) -> None:
    """Run the pipeline for a priority queue: flush → editor → fact-check → publish."""
    events = _curador.flush(priority)
    if not events:
        logger.debug("Pipeline %s: no events to process", priority)
        return

    run_id = str(uuid.uuid4())[:8]
    logger.info("Pipeline %s [%s]: processing %d events", priority, run_id, len(events))

    # Editor-Chefe (1 LLM call per batch)
    approved = await _editor.evaluate_batch(events, priority)
    if not approved:
        logger.info("Pipeline %s [%s]: no events approved by editor", priority, run_id)
        return

    logger.info("Pipeline %s [%s]: %d/%d approved by editor", priority, run_id, len(approved), len(events))

    # Fact-Check + Publish each approved item
    published = 0
    for item in approved:
        # Find original content for AI detection (Bug #1 fix)
        original_event = next(
            (e for e in events if e.raw_event.id == item.id),
            None,
        )
        original_content = original_event.raw_event.content if original_event else ""

        fc_result = await _fact_checker.check(item, original_content)
        success = await _publisher.publish(item, fc_result)
        if success:
            published += 1

    logger.info("Pipeline %s [%s]: %d/%d published", priority, run_id, published, len(approved))


async def run_pipeline() -> None:
    """Main entry: configure and start the APScheduler."""
    scheduler = AsyncIOScheduler()

    # Collector jobs
    for collector_name, interval in COLLECTOR_INTERVALS.items():
        if interval is None:
            continue  # on-demand or cron-only
        scheduler.add_job(
            collect_job,
            "interval",
            minutes=interval,
            args=[collector_name],
            id=f"collector_{collector_name}",
            name=f"Collector: {collector_name}",
            max_instances=1,
        )

    # ACLED: daily at 06:00 UTC
    scheduler.add_job(
        collect_job,
        "cron",
        hour=6,
        minute=0,
        args=["acled"],
        id="collector_acled",
        name="Collector: acled (daily)",
        max_instances=1,
    )

    # Pipeline jobs
    for priority, interval in PIPELINE_INTERVALS.items():
        scheduler.add_job(
            pipeline_job,
            "interval",
            minutes=interval,
            args=[priority],
            id=f"pipeline_{priority.lower()}",
            name=f"Pipeline: {priority}",
            max_instances=1,
        )

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))

    # Keep alive
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        await _editor.close()
        await _fact_checker.close()
        await _publisher.close()
        await _enricher.close()
