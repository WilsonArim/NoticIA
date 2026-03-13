"""Stage 3: Multi-HyDE Embeddings — local sentence-transformers + pgvector storage."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from openclaw.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

logger = logging.getLogger("openclaw.factcheck.embeddings")

HYDE_PREFIXES = [
    "It is reported that ",
    "According to sources, ",
    "Evidence suggests that ",
]


@dataclass
class EmbeddingResult:
    claim: str
    embeddings: list[list[float]] = field(default_factory=list)
    stored: bool = False


class LocalEmbeddings:
    """Generate Multi-HyDE embeddings using all-MiniLM-L6-v2 and store in pgvector."""

    def __init__(self) -> None:
        self._model = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Sentence transformer loaded (384 dimensions)")
            except Exception as e:
                logger.error("Failed to load sentence transformer: %s", e)
                self._model = "failed"

    def generate_embeddings(self, claims: list[str]) -> list[EmbeddingResult]:
        """Generate 3 Multi-HyDE embeddings per claim."""
        self._load_model()
        results = []

        for claim in claims:
            result = EmbeddingResult(claim=claim)

            if self._model and self._model != "failed":
                try:
                    variations = [prefix + claim for prefix in HYDE_PREFIXES]
                    embeddings = self._model.encode(variations)
                    result.embeddings = [emb.tolist() for emb in embeddings]
                except Exception as e:
                    logger.warning("Embedding generation failed for claim: %s", e)

            results.append(result)

        return results

    async def store_embeddings(self, results: list[EmbeddingResult]) -> None:
        """Fix Bug #3: Store generated embeddings in pgvector via claim_embeddings table."""
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            logger.warning("Supabase not configured — skipping embedding storage")
            return

        client = await self._get_client()
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

        for result in results:
            if not result.embeddings:
                continue

            # Average the 3 Multi-HyDE variations as the canonical embedding
            dim = len(result.embeddings[0])
            avg_embedding = [
                sum(emb[i] for emb in result.embeddings) / len(result.embeddings)
                for i in range(dim)
            ]

            try:
                resp = await client.post(
                    f"{SUPABASE_URL}/rest/v1/claim_embeddings",
                    json={
                        "claim_text": result.claim,
                        "embedding": str(avg_embedding),
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                result.stored = True
                logger.debug("Stored embedding for claim: %s", result.claim[:50])
            except Exception as e:
                logger.warning("Failed to store embedding: %s", e)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
