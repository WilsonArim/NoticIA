"""Stage 2: Phantom Source Detector — URL reachability + DOI + WHOIS."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger("openclaw.factcheck.phantom_source")


@dataclass
class SourceCheckResult:
    url: str
    reachable: bool = False
    status_code: int = 0
    doi_valid: bool | None = None
    domain_age_days: int | None = None
    flags: list[str] = field(default_factory=list)


class PhantomSourceDetector:
    """Verify that cited sources actually exist."""

    async def check_sources(self, text: str, urls: list[str] | None = None) -> list[SourceCheckResult]:
        """Check all URLs found in text."""
        if urls is None:
            urls = self._extract_urls(text)

        results = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for url in urls[:20]:  # Cap at 20 URLs
                result = await self._check_url(client, url)
                results.append(result)

        return results

    async def _check_url(self, client: httpx.AsyncClient, url: str) -> SourceCheckResult:
        result = SourceCheckResult(url=url)

        # 1. HEAD request for reachability
        try:
            resp = await client.head(url)
            result.status_code = resp.status_code
            result.reachable = resp.status_code < 400
            if not result.reachable:
                result.flags.append(f"unreachable_status_{resp.status_code}")
        except Exception:
            result.flags.append("unreachable_connection_error")

        # 2. DOI check
        doi_match = re.search(r'10\.\d{4,}/\S+', url)
        if doi_match:
            doi = doi_match.group()
            result.doi_valid = await self._check_doi(client, doi)
            if result.doi_valid is False:
                result.flags.append("invalid_doi")

        # 3. WHOIS domain age (simplified)
        try:
            import whois
            domain = url.split("/")[2] if "/" in url else url
            w = whois.whois(domain)
            if w.creation_date:
                created = w.creation_date
                if isinstance(created, list):
                    created = created[0]
                age = (datetime.utcnow() - created).days
                result.domain_age_days = age
                if age < 30:
                    result.flags.append("new_domain_under_30_days")
        except Exception:
            pass  # WHOIS is optional

        return result

    @staticmethod
    async def _check_doi(client: httpx.AsyncClient, doi: str) -> bool:
        """Validate a DOI via Crossref API."""
        try:
            resp = await client.get(f"https://api.crossref.org/works/{doi}")
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _extract_urls(text: str) -> list[str]:
        """Extract URLs from text."""
        url_pattern = r'https?://[^\s<>\"\')\]]+'
        return re.findall(url_pattern, text)
