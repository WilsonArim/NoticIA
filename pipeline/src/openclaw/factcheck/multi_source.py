"""Stage 5: Multi-Source Verification — Wikipedia + DuckDuckGo + X API v2."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from openclaw.config import X_BEARER_TOKEN

logger = logging.getLogger("openclaw.factcheck.multi_source")


@dataclass
class VerificationResult:
    claim: str
    wikipedia_snippets: list[str] = field(default_factory=list)
    ddg_results: list[str] = field(default_factory=list)
    x_results: list[str] = field(default_factory=list)
    weighted_score: float = 0.0
    verdict: str = "unverifiable"  # cross_reference, limited, none


class MultiSourceVerifier:
    """Verify claims against Wikipedia, DuckDuckGo, and X. Fix Bug #5: validate content vs claim."""

    async def verify_claims(self, claims: list[str]) -> list[VerificationResult]:
        results = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for claim in claims:
                result = await self._verify_claim(client, claim)
                results.append(result)
        return results

    async def _verify_claim(self, client: httpx.AsyncClient, claim: str) -> VerificationResult:
        result = VerificationResult(claim=claim)

        # Source 1: Wikipedia API
        wiki_snippets = await self._search_wikipedia(client, claim)
        result.wikipedia_snippets = wiki_snippets

        # Source 2: DuckDuckGo Instant Answer
        ddg_results = await self._search_duckduckgo(client, claim)
        result.ddg_results = ddg_results

        # Source 3: X API v2 Recent Search
        x_results = await self._search_x(client, claim)
        result.x_results = x_results

        # Fix Bug #5: Validate content actually corroborates the claim
        # Instead of just counting sources, check for semantic overlap
        weighted = 0.0
        claim_words = set(claim.lower().split())
        for snippet in wiki_snippets + ddg_results + x_results:
            snippet_words = set(snippet.lower().split())
            overlap = len(claim_words & snippet_words) / max(len(claim_words), 1)
            if overlap >= 0.3:  # At least 30% word overlap
                weighted += 1.0

        result.weighted_score = weighted
        if weighted >= 3.0:
            result.verdict = "cross_reference"
        elif weighted >= 1.0:
            result.verdict = "limited"
        else:
            result.verdict = "none"

        return result

    @staticmethod
    async def _search_wikipedia(client: httpx.AsyncClient, query: str) -> list[str]:
        try:
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query[:100],
                    "srlimit": 5,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [r.get("snippet", "") for r in data.get("query", {}).get("search", [])]
        except Exception:
            return []

    @staticmethod
    async def _search_duckduckgo(client: httpx.AsyncClient, query: str) -> list[str]:
        try:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query[:100], "format": "json", "no_html": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            if data.get("AbstractText"):
                results.append(data["AbstractText"])
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(topic["Text"])
            return results
        except Exception:
            return []

    @staticmethod
    async def _search_x(client: httpx.AsyncClient, query: str) -> list[str]:
        """Search X API v2 Recent Search for claim verification."""
        if not X_BEARER_TOKEN:
            return []
        try:
            resp = await client.get(
                "https://api.x.com/2/tweets/search/recent",
                params={
                    "query": query[:256] + " lang:en -is:retweet",
                    "max_results": 10,
                    "tweet.fields": "text,author_id,created_at",
                },
                headers={"Authorization": f"Bearer {X_BEARER_TOKEN}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return [tweet["text"] for tweet in data.get("data", []) if tweet.get("text")]
        except Exception:
            return []
