"""Runner bridge — delegates to scheduler_ollama."""
import asyncio
import logging
import sys
from pathlib import Path

# Ensure pipeline root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from openclaw.scheduler_ollama import scheduler

logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    """Start the OpenClaw pipeline scheduler."""
    logger.info("OpenClaw Pipeline starting via scheduler_ollama...")
    scheduler.start()
    logger.info("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
