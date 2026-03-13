"""OpenClaw News Pipeline — Entry Point."""
import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from openclaw.scheduler.runner import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("openclaw")


def main() -> None:
    """Start the OpenClaw pipeline."""
    logger.info("OpenClaw Pipeline v2.0 starting...")
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")
    except Exception as e:
        logger.critical("Pipeline crashed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
