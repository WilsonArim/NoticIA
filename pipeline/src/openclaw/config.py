"""Central configuration for the OpenClaw pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


# --- Environment ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
PUBLISH_API_KEY = os.getenv("PUBLISH_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = "https://api.x.ai/v1"
XAI_MODEL = "grok-4.1-fast"
EVENT_REGISTRY_API_KEY = os.getenv("EVENT_REGISTRY_API_KEY", "")
ACLED_API_KEY = os.getenv("ACLED_API_KEY", "")
ACLED_EMAIL = os.getenv("ACLED_EMAIL", "")
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# --- Edge Function URLs ---
EDGE_FUNCTION_BASE = f"{SUPABASE_URL}/functions/v1"
EDGE_RECEIVE_ARTICLE = f"{EDGE_FUNCTION_BASE}/receive-article"
EDGE_RECEIVE_CLAIMS = f"{EDGE_FUNCTION_BASE}/receive-claims"
EDGE_RECEIVE_RATIONALE = f"{EDGE_FUNCTION_BASE}/receive-rationale"
EDGE_AGENT_LOG = f"{EDGE_FUNCTION_BASE}/agent-log"

# --- GDELT Queries (14 areas) ---
GDELT_QUERIES: dict[str, str] = {
    "geopolitics": "sanctions OR diplomacy OR nato OR sovereignty OR territorial dispute",
    "defense": "military OR missile OR armed forces OR weapons OR deployment OR drone strike",
    "economy": "GDP OR inflation OR central bank OR recession OR trade deficit OR tariff",
    "tech": "artificial intelligence OR semiconductor OR cybersecurity OR quantum computing OR data breach",
    "energy": "oil price OR OPEC OR renewable energy OR pipeline OR nuclear energy OR LNG",
    "health": "pandemic OR vaccine OR WHO OR outbreak OR clinical trial OR epidemic",
    "environment": "climate change OR deforestation OR wildfire OR biodiversity OR emissions OR carbon",
    "crypto": "bitcoin OR ethereum OR cryptocurrency OR blockchain OR DeFi OR stablecoin",
    "regulation": "regulation OR legislation OR antitrust OR GDPR OR supreme court OR sanctions law",
    "portugal": "Portugal OR Lisbon OR Portuguese government",
    "science": "NASA OR ESA OR genome OR CRISPR OR discovery OR peer review OR particle physics",
    "financial_markets": "stock market OR Nasdaq OR bond yield OR forex OR commodities OR earnings",
    "society": "protest OR human rights OR refugee OR migration OR inequality OR censorship",
    "sports": "FIFA OR UEFA OR Olympics OR doping OR World Cup OR corruption sport",
}

# --- Breaking Signals (force P1) ---
BREAKING_SIGNALS: list[str] = [
    "breaking", "just in", "urgent", "flash", "developing",
    "explosion", "earthquake", "tsunami", "coup", "assassination",
    "missile", "nuclear", "invasion", "martial law",
    "state of emergency", "war declared", "ceasefire",
    "pandemic", "outbreak",
]

# --- Priority Queue Caps ---
QUEUE_CAPS = {"P1": 10, "P2": 25, "P3": 30}
MAX_PER_AREA_IN_FLUSH = 3
SEEN_HASHES_CAP = 10_000
SEEN_TITLES_CAP = 10_000  # Fix Bug #6
TITLE_SIMILARITY_THRESHOLD = 0.85

# --- Editor-Chefe Temperatures ---
EDITOR_TEMPERATURES = {"P1": 0.1, "P2": 0.3, "P3": 0.4}

# --- Circuit Breaker ---
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_PAUSE_SECONDS = 60
RETRY_MAX = 3
RETRY_BACKOFF_BASE = 2  # seconds: 2, 4, 8

# --- Fact-Check Thresholds ---
AI_DETECTION_CONFIRMED_THRESHOLD = 0.85
AI_DETECTION_SUSPECTED_THRESHOLD = 0.60
AI_HEURISTIC_PHRASES = [
    "as an ai", "it's important to note", "it is worth mentioning",
    "in conclusion", "it should be noted", "as a language model",
    "i don't have personal", "it's crucial to", "delve into",
    "it's essential to", "navigate the complexities",
    "in today's rapidly", "the landscape of",
]

# --- Scheduler Intervals (minutes) ---
COLLECTOR_INTERVALS = {
    "gdelt": 15,
    "event_registry": 15,
    "acled": None,  # cron: daily 06:00 UTC
    "rss": 10,
    "telegram": 5,
    "crawl4ai": None,  # on-demand
}
PIPELINE_INTERVALS = {"P1": 30, "P2": 180, "P3": 720}

# --- FinOps ---
XAI_PRICING = {"input_per_m": 5.0, "output_per_m": 15.0}  # USD


@dataclass
class ReporterConfig:
    """Configuration for a single reporter."""
    area: str
    threshold: float = 0.30
    max_score_divisor: float = 15.0
    priority_collectors: list[str] = field(default_factory=list)
    weighted_keywords: dict[int, list[str]] = field(default_factory=dict)
