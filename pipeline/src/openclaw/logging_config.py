"""
Structured JSON logging with file rotation for the NoticIA pipeline.

Usage (import once at startup — scheduler_ollama.py):
    from openclaw.logging_config import setup_logging
    setup_logging()

All other modules simply use:
    import logging
    logger = logging.getLogger(__name__)

Outputs:
    - Console:  human-readable (coloured) for dev, JSON in production
    - File:     JSON lines → /var/log/noticia/pipeline.jsonl (rotated, 10MB x 5)
"""
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields (agent, event_id, etc.) if provided
        for key in ("agent", "event_id", "stage", "duration_ms", "tokens", "cost_usd"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Human-readable coloured output for interactive terminals."""

    COLORS = {
        "DEBUG": "\033[36m",    # cyan
        "INFO": "\033[32m",     # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[35m", # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        return f"{ts} {color}{record.levelname:7s}{self.RESET} [{record.name}] {record.getMessage()}"


def setup_logging(
    level: str = "INFO",
    log_dir: str = "/var/log/noticia",
    log_file: str = "pipeline.jsonl",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    force_json_console: bool = False,
) -> None:
    """Configure root logger with structured JSON logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Directory for log files. Created if missing.
        log_file: Name of the rotating log file.
        max_bytes: Max size per log file before rotation.
        backup_count: Number of rotated files to keep.
        force_json_console: Force JSON on console even in TTY mode.
    """
    # Override from environment
    level = os.getenv("LOG_LEVEL", level).upper()
    log_dir = os.getenv("LOG_DIR", log_dir)
    force_json = os.getenv("LOG_FORMAT", "").lower() == "json" or force_json_console

    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    # Clear any existing handlers (prevents duplicate logs)
    root.handlers.clear()

    # ── Console handler ──────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stderr)
    if force_json or not sys.stderr.isatty():
        # Docker / CI / redirected → JSON
        console.setFormatter(JsonFormatter())
    else:
        # Interactive terminal → human-readable
        console.setFormatter(HumanFormatter())
    root.addHandler(console)

    # ── File handler (rotating JSON lines) ───────────────────────────────
    try:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)
    except PermissionError:
        # In Docker without /var/log mount, skip file logging gracefully
        root.warning(
            "Cannot write to %s — file logging disabled. "
            "Mount a volume or set LOG_DIR env var.",
            log_dir,
        )

    # Quiet noisy libraries
    for lib in ("httpx", "httpcore", "hpack", "urllib3", "asyncio", "apscheduler.executors"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    root.info(
        "Logging initialised: level=%s, console=%s, file=%s/%s",
        level,
        "json" if (force_json or not sys.stderr.isatty()) else "human",
        log_dir,
        log_file,
    )
