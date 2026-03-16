"""Reporter scoring engine — 0 LLM tokens, pure keyword matching."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

from openclaw.config import (
    BREAKING_SIGNALS,
    ReporterConfig,
)
from openclaw.models import RawEvent, ScoredEvent

logger = logging.getLogger("openclaw.reporters")


@lru_cache(maxsize=512)
def _word_pattern(term: str) -> re.Pattern[str]:
    """Compile a word-boundary regex for a keyword. Cached for performance."""
    return re.compile(r"\b" + re.escape(term.lower()) + r"\b", re.IGNORECASE)


def _keyword_matches(term: str, text: str) -> bool:
    """Check if a keyword matches in text using word boundaries."""
    return _word_pattern(term).search(text) is not None


# --- 14 Reporter Configurations ---

REPORTER_CONFIGS: dict[str, ReporterConfig] = {
    "geopolitics": ReporterConfig(
        area="geopolitics",
        threshold=0.30,
        priority_collectors=["gdelt", "acled", "event_registry"],
        weighted_keywords={
            5: ["sanctions", "sovereignty", "territorial dispute", "annexation", "nato expansion"],
            4: ["diplomacy", "nato", "un resolution", "ceasefire", "peace talks", "alliance"],
            3: ["embargo", "treaty", "bilateral", "multilateral", "summit", "g7", "g20"],
            2: ["foreign minister", "ambassador", "consulate", "diplomatic"],
            1: ["international", "geopolitical", "relations"],
        },
    ),
    "defense": ReporterConfig(
        area="defense",
        threshold=0.30,
        priority_collectors=["gdelt", "acled"],
        weighted_keywords={
            5: ["missile strike", "nuclear weapon", "invasion", "air strike", "drone strike"],
            4: ["military", "armed forces", "deployment", "warship", "fighter jet", "artillery"],
            3: ["weapons", "ammunition", "defense budget", "military exercise", "special forces"],
            2: ["veteran", "base", "regiment", "battalion", "brigade"],
            1: ["security", "defense", "military aid"],
        },
    ),
    "economy": ReporterConfig(
        area="economy",
        threshold=0.30,
        priority_collectors=["event_registry", "rss"],
        weighted_keywords={
            5: ["recession", "financial crisis", "bank collapse", "hyperinflation", "default"],
            4: ["GDP", "inflation", "central bank", "interest rate", "trade deficit", "tariff"],
            3: ["unemployment", "fiscal policy", "monetary policy", "stimulus", "austerity"],
            2: ["economic growth", "consumer spending", "supply chain", "manufacturing"],
            1: ["economy", "market", "business", "trade"],
        },
    ),
    "tech": ReporterConfig(
        area="tech",
        threshold=0.30,
        priority_collectors=["rss", "x"],
        weighted_keywords={
            5: ["artificial intelligence", "AGI", "quantum computing", "zero-day", "data breach"],
            4: ["semiconductor", "cybersecurity", "LLM", "machine learning", "neural network"],
            3: ["open source", "API", "cloud computing", "blockchain tech", "encryption"],
            2: ["startup", "tech company", "silicon valley", "software", "hardware"],
            1: ["technology", "digital", "innovation", "computing"],
        },
    ),
    "energy": ReporterConfig(
        area="energy",
        threshold=0.30,
        priority_collectors=["event_registry", "rss"],
        weighted_keywords={
            5: ["oil embargo", "energy crisis", "nuclear meltdown", "pipeline explosion"],
            4: ["oil price", "OPEC", "renewable energy", "nuclear energy", "LNG"],
            3: ["solar", "wind power", "electric grid", "energy transition", "carbon capture"],
            2: ["natural gas", "petroleum", "refinery", "power plant", "electricity"],
            1: ["energy", "fuel", "power", "utilities"],
        },
    ),
    "health": ReporterConfig(
        area="health",
        threshold=0.30,
        priority_collectors=["rss", "event_registry"],
        weighted_keywords={
            5: ["pandemic", "outbreak", "epidemic", "WHO emergency", "novel virus"],
            4: ["vaccine", "WHO", "clinical trial", "mortality rate", "quarantine"],
            3: ["public health", "hospital", "drug approval", "treatment", "diagnosis"],
            2: ["medical", "healthcare", "pharmaceutical", "disease", "infection"],
            1: ["health", "medicine", "wellness", "patient"],
        },
    ),
    "environment": ReporterConfig(
        area="environment",
        threshold=0.30,
        priority_collectors=["gdelt", "rss"],
        weighted_keywords={
            5: ["climate emergency", "mass extinction", "ecological collapse"],
            4: ["climate change", "deforestation", "wildfire", "emissions", "carbon"],
            3: ["biodiversity", "pollution", "ocean warming", "ice sheet", "coral reef"],
            2: ["sustainability", "conservation", "renewable", "ecosystem", "habitat"],
            1: ["environment", "green", "nature", "ecological"],
        },
    ),
    "crypto": ReporterConfig(
        area="crypto",
        threshold=0.30,
        priority_collectors=["x", "rss"],
        weighted_keywords={
            5: ["exchange hack", "rug pull", "SEC crypto", "stablecoin depeg", "protocol exploit"],
            4: ["bitcoin", "ethereum", "cryptocurrency", "DeFi", "stablecoin", "NFT"],
            3: ["blockchain", "mining", "wallet", "token", "smart contract", "DAO"],
            2: ["crypto exchange", "trading", "liquidity", "yield", "airdrop"],
            1: ["crypto", "digital asset", "web3", "decentralized"],
        },
    ),
    "regulation": ReporterConfig(
        area="regulation",
        threshold=0.30,
        priority_collectors=["event_registry", "rss"],
        weighted_keywords={
            5: ["supreme court ruling", "antitrust action", "emergency legislation"],
            4: ["regulation", "legislation", "antitrust", "GDPR", "sanctions law"],
            3: ["compliance", "legal ruling", "court order", "constitutional", "statute"],
            2: ["regulatory", "law enforcement", "prosecutor", "judicial"],
            1: ["law", "legal", "regulation", "court"],
        },
    ),
    "portugal": ReporterConfig(
        area="portugal",
        threshold=0.25,  # Lower threshold for local news
        priority_collectors=["rss", "gdelt"],
        weighted_keywords={
            5: ["portugal crisis", "governo demissao", "assembleia voto"],
            4: ["Portugal", "Lisbon", "Portuguese government", "Lisboa", "governo portugues"],
            3: ["parlamento", "primeiro-ministro", "banco de portugal", "INE"],
            2: ["portuguesa", "portugues", "nacional", "republica"],
            1: ["PT", "luso", "iberico"],
        },
    ),
    "science": ReporterConfig(
        area="science",
        threshold=0.30,
        priority_collectors=["rss", "event_registry"],
        weighted_keywords={
            5: ["Nobel Prize", "breakthrough discovery", "new species discovered"],
            4: ["NASA", "ESA", "genome", "CRISPR", "peer review", "particle physics"],
            3: ["research paper", "clinical study", "laboratory", "experiment", "hypothesis"],
            2: ["scientist", "professor", "university", "publication", "journal"],
            1: ["science", "research", "study", "discovery"],
        },
    ),
    "financial_markets": ReporterConfig(
        area="financial_markets",
        threshold=0.30,
        priority_collectors=["rss", "x"],
        weighted_keywords={
            5: ["market crash", "flash crash", "circuit breaker triggered", "margin call"],
            4: ["stock market", "Nasdaq", "bond yield", "forex", "commodities", "earnings"],
            3: ["S&P 500", "dow jones", "bull market", "bear market", "IPO", "merger"],
            2: ["trading", "investor", "portfolio", "dividend", "valuation"],
            1: ["market", "stocks", "shares", "financial"],
        },
    ),
    "society": ReporterConfig(
        area="society",
        threshold=0.30,
        priority_collectors=["gdelt", "rss"],
        weighted_keywords={
            5: ["mass protest", "civil war", "genocide", "ethnic cleansing"],
            4: ["protest", "human rights", "refugee", "migration", "inequality", "censorship"],
            3: ["civil liberties", "freedom of press", "discrimination", "asylum", "deportation"],
            2: ["community", "social justice", "activism", "NGO", "charity"],
            1: ["society", "social", "people", "public"],
        },
    ),
    "sports": ReporterConfig(
        area="sports",
        threshold=0.35,  # Higher threshold — less noise
        priority_collectors=["rss", "x"],
        weighted_keywords={
            5: ["doping scandal", "match fixing", "corruption sport", "ban lifetime"],
            4: ["FIFA", "UEFA", "Olympics", "World Cup", "Champions League"],
            3: ["transfer", "tournament", "championship", "medal", "record"],
            2: ["football", "soccer", "basketball", "tennis", "Formula 1"],
            1: ["sport", "athlete", "team", "match", "game"],
        },
    ),
    "intl_politics": ReporterConfig(
        area="intl_politics",
        threshold=0.30,
        priority_collectors=["gdelt", "event_registry"],
        weighted_keywords={
            5: ["regime change", "coup d'état", "political crisis", "government collapse", "impeachment"],
            4: ["election", "prime minister", "president elected", "parliament dissolved", "political turmoil"],
            3: ["opposition leader", "coalition government", "political party", "referendum", "vote of confidence", "constitutional crisis"],
            2: ["head of state", "cabinet reshuffle", "political reform", "inauguration", "term limit"],
            1: ["politics", "political", "government", "democracy", "authoritarian"],
        },
    ),
    "diplomacy": ReporterConfig(
        area="diplomacy",
        threshold=0.30,
        priority_collectors=["gdelt", "event_registry"],
        weighted_keywords={
            5: ["peace agreement", "ambassador expelled", "diplomatic crisis", "embassy closure", "diplomatic immunity revoked"],
            4: ["UN summit", "peace talks", "treaty signed", "diplomatic relations", "foreign affairs minister"],
            3: ["bilateral agreement", "multilateral negotiations", "consular services", "diplomatic channel", "envoy", "mediation"],
            2: ["diplomatic visit", "state visit", "memorandum of understanding", "protocol", "accreditation"],
            1: ["diplomacy", "diplomatic", "foreign affairs", "embassy", "consul"],
        },
    ),
    "defense_strategy": ReporterConfig(
        area="defense_strategy",
        threshold=0.30,
        priority_collectors=["gdelt", "acled"],
        weighted_keywords={
            5: ["arms race", "nuclear proliferation", "defense pact", "military buildup", "strategic deterrence"],
            4: ["defense budget", "arms deal", "military alliance", "naval exercise", "weapons procurement"],
            3: ["defense minister", "joint military exercise", "arms embargo", "military cooperation", "defense industry", "conscription"],
            2: ["defense spending", "strategic partnership", "military modernization", "arms export", "defense contractor"],
            1: ["defense strategy", "strategic", "military planning", "national security", "deterrence"],
        },
    ),
    "disinfo": ReporterConfig(
        area="disinfo",
        threshold=0.35,  # Higher threshold — critical reporter, less noise
        priority_collectors=["x", "rss"],
        weighted_keywords={
            5: ["fake news", "deep fake", "propaganda", "bot network", "manipulation", "disinformation", "misinformation", "astroturfing", "troll farm"],
            4: ["information warfare", "media manipulation", "coordinated inauthentic", "fact check failed", "fabricated content", "election interference"],
            3: ["false narrative", "conspiracy theory", "influence operation", "state propaganda", "censorship", "media control", "content moderation"],
            2: ["misleading", "debunked", "viral hoax", "clickbait", "echo chamber", "filter bubble"],
            1: ["information", "narrative", "credibility", "verification", "media literacy"],
        },
    ),
    "human_rights": ReporterConfig(
        area="human_rights",
        threshold=0.30,
        priority_collectors=["gdelt", "acled"],
        weighted_keywords={
            5: ["genocide", "ethnic cleansing", "political prisoner", "war crime", "crimes against humanity"],
            4: ["torture", "forced disappearance", "freedom of press", "human rights violation", "humanitarian crisis"],
            3: ["arbitrary detention", "extrajudicial killing", "press freedom", "civil liberties", "asylum seeker", "persecution"],
            2: ["human rights watch", "amnesty international", "ICC", "UN human rights", "UNHCR"],
            1: ["human rights", "rights", "dignity", "freedom", "liberty"],
        },
    ),
    "organized_crime": ReporterConfig(
        area="organized_crime",
        threshold=0.30,
        priority_collectors=["event_registry", "rss"],
        weighted_keywords={
            5: ["drug cartel", "money laundering", "organized crime ring", "human trafficking", "narco state"],
            4: ["drug trafficking", "mafia", "criminal network", "corruption scandal", "extortion ring"],
            3: ["drug seizure", "criminal organization", "smuggling", "racketeering", "illicit trade", "arms trafficking"],
            2: ["law enforcement raid", "undercover operation", "witness protection", "criminal enterprise", "syndicate"],
            1: ["crime", "criminal", "trafficking", "smuggling", "cartel"],
        },
    ),
}


def score_event(event: RawEvent, config: ReporterConfig) -> float:
    """Score an event based on weighted keywords × source credibility."""
    text = f"{event.title} {event.content}".lower()

    # 1. Keyword matching with weights (1-5), using word boundaries
    weighted_sum = 0
    matched: list[str] = []
    for weight, terms in config.weighted_keywords.items():
        for term in terms:
            if _keyword_matches(term, text):
                weighted_sum += weight
                matched.append(term)

    if weighted_sum == 0:
        return 0.0

    # 2. Normalize
    score = min(weighted_sum / config.max_score_divisor, 1.0)

    # 3. Boost for priority collectors (+30%)
    if event.source_collector in config.priority_collectors:
        score *= 1.3

    # 4. Temporal boost
    age_hours = (datetime.utcnow() - event.published_at).total_seconds() / 3600
    if age_hours < 1:
        score *= 1.2
    elif age_hours < 6:
        score *= 1.1

    # 5. Source credibility weight (from metadata or default 0.5)
    credibility_weight = event.raw_metadata.get("credibility_weight", 0.5)
    score *= credibility_weight

    return min(score, 1.0)


def classify_priority(score: float, event: RawEvent, threshold: float) -> str:
    """Classify event priority: P1 (urgent), P2 (relevant), P3 (context)."""
    text = f"{event.title} {event.content}".lower()

    # Breaking signals → force P1 (word boundary match)
    for signal in BREAKING_SIGNALS:
        if _keyword_matches(signal, text):
            return "P1"

    # ACLED fatalities → P1
    if event.raw_metadata.get("is_breaking"):
        return "P1"

    if score >= 0.70:
        return "P1"
    elif score >= 0.40:
        return "P2"
    elif score >= threshold:
        return "P3"
    return ""  # Discard


class BaseReporter:
    """A reporter scores all events from the common table for its area."""

    def __init__(self, config: ReporterConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(f"openclaw.reporter.{config.area}")

    def score_events(self, events: list[RawEvent]) -> list[ScoredEvent]:
        """Score all events, return those above threshold."""
        scored: list[ScoredEvent] = []
        for event in events:
            s = score_event(event, self.config)
            if s < self.config.threshold:
                continue
            priority = classify_priority(s, event, self.config.threshold)
            if not priority:
                continue

            text = f"{event.title} {event.content}".lower()
            matched = []
            for weight, terms in self.config.weighted_keywords.items():
                for term in terms:
                    if _keyword_matches(term, text):
                        matched.append(term)

            scored.append(ScoredEvent(
                raw_event=event,
                area=self.config.area,
                score=s,
                matched_keywords=matched,
                priority=priority,
            ))
        self.logger.info(
            "Reporter '%s': %d/%d events scored above threshold %.2f",
            self.config.area, len(scored), len(events), self.config.threshold,
        )
        return scored


def create_all_reporters() -> list[BaseReporter]:
    """Create all 20 reporters from configs."""
    return [BaseReporter(config) for config in REPORTER_CONFIGS.values()]
