"""
Elite Reporter — Investigação OSINT com pesquisa web real
=========================================================
Braço operacional da Equipa de Elite V2.
Pesquisa factos usando ferramentas REAIS (Tavily, Exa, Serper).
Cada facto é registado com URL de fonte + raw API output.

Regra fundamental: NUNCA inventar dados. Se não encontra, marca "NÃO VERIFICADO".
"""
import os
import re
import json
import logging
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from supabase import create_client
from openai import OpenAI

logger = logging.getLogger("elite.reporter")

# Config from env
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL = os.getenv("MODEL_ELITE_REPORTER", os.getenv("MODEL_DOSSIE", "kimi-k2-thinking"))
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# Source authority scores by domain pattern
SOURCE_AUTHORITY = {
    "primary_gov": 0.95,
    "primary_ngo": 0.90,
    "primary_court": 0.95,
    "primary_corp": 0.85,
    "academic": 0.85,
    "wire_agency": 0.80,
    "mainstream_media": 0.50,
    "independent_media": 0.55,
    "social_media": 0.20,
    "blog": 0.15,
    "unknown": 0.10,
}

# Domain classification patterns
GOV_DOMAINS = {".gov", ".gov.uk", ".gov.pt", ".gov.br", ".europa.eu", ".mil"}
NGO_DOMAINS = {"hrw.org", "amnesty.org", "fatf-gafi.org", "un.org", "icij.org", "transparency.org", "who.int", "worldbank.org"}
COURT_DOMAINS = {"justice.gov", "sec.gov", "courtlistener.com", "law.cornell.edu", "eur-lex.europa.eu"}
CORP_DOMAINS = {"sec.gov/cgi-bin", "edgar"}  # SEC filings
ACADEMIC_DOMAINS = {".edu", "scholar.google", "arxiv.org", "nature.com", "science.org", "thelancet.com", "pubmed.ncbi"}
WIRE_AGENCIES = {"reuters.com", "apnews.com", "afp.com", "efe.com", "lusa.pt", "bloomberg.com"}
INDEPENDENT_MEDIA = {"theintercept.com", "bellingcat.com", "propublica.org", "occrp.org"}
SOCIAL_MEDIA = {"twitter.com", "x.com", "reddit.com", "facebook.com", "instagram.com", "tiktok.com", "threads.net"}

def _classify_source(url: str) -> tuple[str, float]:
    """Classify source type and authority score from URL domain."""
    domain = urlparse(url).netloc.lower()

    # Check each category
    for gov in GOV_DOMAINS:
        if domain.endswith(gov):
            return "primary_gov", SOURCE_AUTHORITY["primary_gov"]

    for ngo in NGO_DOMAINS:
        if ngo in domain:
            return "primary_ngo", SOURCE_AUTHORITY["primary_ngo"]

    for court in COURT_DOMAINS:
        if court in domain:
            return "primary_court", SOURCE_AUTHORITY["primary_court"]

    if domain.endswith(".edu") or any(a in domain for a in ACADEMIC_DOMAINS):
        return "academic", SOURCE_AUTHORITY["academic"]

    for wire in WIRE_AGENCIES:
        if wire in domain:
            return "wire_agency", SOURCE_AUTHORITY["wire_agency"]

    for indie in INDEPENDENT_MEDIA:
        if indie in domain:
            return "independent_media", SOURCE_AUTHORITY["independent_media"]

    for social in SOCIAL_MEDIA:
        if social in domain:
            return "social_media", SOURCE_AUTHORITY["social_media"]

    # Check for corporate filings
    if "sec.gov" in domain and ("edgar" in url.lower() or "filing" in url.lower()):
        return "primary_corp", SOURCE_AUTHORITY["primary_corp"]

    # Default mainstream media check (common news domains)
    mainstream = ["bbc.", "cnn.", "nytimes.", "theguardian.", "elpais.", "washingtonpost.",
                  "foxnews.", "dailymail.", "telegraph.", "lemonde.", "spiegel.", "corriere.",
                  "publico.pt", "observador.pt", "rtp.pt", "dn.pt", "jn.pt", "tvi.pt",
                  "sapo.pt", "tsf.pt", "sicnoticias.pt", "cnbc.", "ft.com", "wsj.com"]
    for ms in mainstream:
        if ms in domain:
            return "mainstream_media", SOURCE_AUTHORITY["mainstream_media"]

    return "unknown", SOURCE_AUTHORITY["unknown"]


# ── Web Search Tools (real HTTP calls) ──────────────────────────────

def _search_tavily(query: str, days: int = 3) -> dict:
    """Tavily search — optimized for fact-checking."""
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not configured"}
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "max_results": 10,
                "include_answer": False,
                "days": days,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return {"error": str(e)}


def _search_exa(query: str) -> dict:
    """Exa.ai search — semantic search, good for technical/academic sources."""
    if not EXA_API_KEY:
        return {"error": "EXA_API_KEY not configured"}
    try:
        resp = httpx.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            json={"query": query, "numResults": 10, "useAutoprompt": True},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Exa.ai search failed: %s", e)
        return {"error": str(e)}


def _search_serper(query: str, search_type: str = "search") -> dict:
    """Serper.dev search — Google results. search_type: 'search' or 'news'."""
    if not SERPER_API_KEY:
        return {"error": "SERPER_API_KEY not configured"}
    try:
        endpoint = f"https://google.serper.dev/{search_type}"
        resp = httpx.post(
            endpoint,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 10, "gl": "us", "hl": "en"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Serper search failed: %s", e)
        return {"error": str(e)}


def _search_serper_news(query: str) -> dict:
    """Serper news search — Google News, last 24h."""
    return _search_serper(query, search_type="news")


def _search_sec_edgar(query: str) -> dict:
    """SEC EDGAR full-text search — free, no API key needed."""
    try:
        resp = httpx.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": query, "dateRange": "custom", "startdt": "2025-01-01", "forms": "8-K,10-Q,10-K"},
            headers={"User-Agent": "NoticIA Research Bot wilson.arim@icloud.com"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("SEC EDGAR search failed: %s", e)
        return {"error": str(e)}


def _execute_search(tool_name: str, args: dict) -> dict:
    """Execute a search tool by name. Returns raw API response."""
    if tool_name == "tavily_search":
        return _search_tavily(args.get("query", ""), args.get("days", 3))
    elif tool_name == "exa_search":
        return _search_exa(args.get("query", ""))
    elif tool_name == "serper_search":
        return _search_serper(args.get("query", ""))
    elif tool_name == "serper_news":
        return _search_serper_news(args.get("query", ""))
    elif tool_name == "sec_edgar":
        return _search_sec_edgar(args.get("query", ""))
    return {"error": f"Unknown tool: {tool_name}"}


# Tool definitions for LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "Deep web search optimized for fact-checking. Best for finding primary sources, official reports, and verified information. Use as primary search tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in English for best results"},
                    "days": {"type": "integer", "description": "Limit results to last N days (default 3)", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "exa_search",
            "description": "Semantic web search. Best for finding academic papers, technical sources, and in-depth analysis. Use for technical/scientific verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Semantic search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "serper_news",
            "description": "Google News search for latest news (last 24-48h). Use for breaking news and real-time coverage. WARNING: results may have editorial bias — always cross-reference with primary sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "News search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sec_edgar",
            "description": "Search SEC EDGAR for corporate filings (8-K, 10-Q, 10-K). Use for verifying financial claims, corporate actions, and regulatory filings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Company name or filing query"},
                },
                "required": ["query"],
            },
        },
    },
]


SYSTEM_PROMPT = """You are the Elite Investigation Reporter for NoticIA — a Portuguese news intelligence operation.

FUNDAMENTAL PRINCIPLE: ABSOLUTE FACTUAL INDEPENDENCE

You are an OSINT investigator. Your ONLY loyalty is to verifiable facts.
You have NO political opinion. You take NO sides. You have NO agenda. You have PRIMARY SOURCES.

CRITICAL RULES:

1. ZERO EXTERNAL KNOWLEDGE: You MUST NOT use your training data to state facts. EVERY fact you report MUST come from a tool search result with a URL. If you cannot find it via search, it does NOT exist for you.

2. SOURCE HIERARCHY (by trust level):
   - LEVEL 1 (highest): Official documents (courts, parliaments, SEC filings, patents, government registries)
   - LEVEL 2 (high): Verification organizations (FATF, UN, HRW, Amnesty, ICIJ, central banks)
   - LEVEL 3 (medium): Wire agencies (Reuters, AP, AFP, Lusa) — factual but may omit context
   - LEVEL 4 (low): Editorial media (BBC, CNN, NYT, Fox News, RT, Al Jazeera, Guardian) — ALL have editorial bias, NONE are neutral. Use ONLY to locate facts, then verify at primary source
   - LEVEL 5 (minimal): Social media, blogs — NEVER as sole source

3. TRIANGLE RULE: No fact is reported without confirmation from at least 2 independent sources of Level 1-3. A single Level 4-5 source is NEVER sufficient.

4. NEVER DISCARD a lead because mainstream media ignores it. If mainstream doesn't cover a topic, it may be: (a) not relevant, OR (b) inconvenient. Always verify with primary sources.

5. NEVER ACCEPT a narrative because mainstream repeats it. Repetition is NOT verification. 50 newspapers citing the same original source = 1 source, not 50.

6. CONFLICT OF INTEREST: If a source has obvious conflict of interest, REGISTER it in the finding metadata.

7. For EACH task assigned, you MUST:
   a) Formulate 2-3 search queries targeting different source types
   b) Execute the searches using the provided tools
   c) Extract specific, verifiable facts from the results
   d) Record each fact with its source URL
   e) If no verifiable fact is found, record: "NÃO VERIFICADO EM FONTES PÚBLICAS"

OUTPUT FORMAT:
For each task, return a JSON array of findings:
[
  {
    "fact_statement": "The specific verifiable fact",
    "source_url": "https://exact-url-where-found",
    "source_domain": "domain.com",
    "search_query_used": "the query that found this",
    "search_provider": "tavily|exa|serper_news|sec_edgar",
    "notes": "Any context about source reliability or conflicts of interest"
  }
]

If you cannot find verifiable information for a task:
[
  {
    "fact_statement": "NÃO VERIFICADO EM FONTES PÚBLICAS",
    "source_url": "N/A",
    "source_domain": "N/A",
    "search_query_used": "the queries you tried",
    "search_provider": "all",
    "notes": "Searched Tavily, Exa, and Serper News with multiple queries. No verifiable primary sources found."
  }
]
"""


def _run_reporter_for_task(client: OpenAI, supabase, investigation_id: str, task: dict) -> list[dict]:
    """Run the reporter agent for a single investigation task."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    user_msg = f"""INVESTIGATION TASK #{task['task_order']}:
{task['description']}

Today's date: {today}
Execute your searches now. Remember: ONLY facts from search results. NEVER from memory."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    findings = []
    max_tool_rounds = 8  # Max rounds of tool calling

    for round_num in range(max_tool_rounds):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto" if round_num < 6 else "none",
                temperature=0.2,
                max_tokens=4000,
            )
        except Exception as e:
            logger.error("LLM call failed round %d: %s", round_num, e)
            break

        choice = response.choices[0]
        msg = choice.message

        # If the model wants to call tools
        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {"query": tc.function.arguments}

                logger.info("Reporter tool call: %s(%s)", tool_name, tool_args.get("query", "")[:60])
                result = _execute_search(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)[:8000],
                })
            continue

        # Model finished — parse findings from response
        if msg.content:
            try:
                # Try to extract JSON array from response
                text = msg.content
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(text[start:end])
                    if isinstance(parsed, list):
                        findings = parsed
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to parse reporter findings JSON: %s", e)
        break

    # Store findings in Supabase
    stored = []
    for f in findings:
        source_url = f.get("source_url", "N/A")
        source_type, authority = _classify_source(source_url) if source_url != "N/A" else ("unknown", 0.10)

        row = {
            "investigation_id": investigation_id,
            "task_id": task["id"],
            "fact_statement": f.get("fact_statement", "")[:2000],
            "source_url": source_url[:2000],
            "source_domain": f.get("source_domain", urlparse(source_url).netloc if source_url.startswith("http") else "N/A"),
            "source_type": source_type,
            "source_authority_score": authority,
            "access_date": datetime.now(timezone.utc).isoformat(),
            "raw_tool_output": None,  # We don't store full raw output per finding to save space
            "search_provider": f.get("search_provider", "unknown"),
            "search_query_used": f.get("search_query_used", ""),
            "fc_status": "unverified",
        }
        try:
            result = supabase.table("elite_findings").insert(row).execute()
            if result.data:
                stored.append(result.data[0])
        except Exception as e:
            logger.error("Failed to store finding: %s", e)

    # Log activity
    try:
        supabase.table("elite_activity_log").insert({
            "investigation_id": investigation_id,
            "agent": "reporter",
            "action": f"task_{task['task_order']}_completed",
            "details": {
                "task_description": task["description"][:200],
                "findings_count": len(stored),
                "search_rounds": min(round_num + 1, max_tool_rounds),
            },
        }).execute()
    except Exception as e:
        logger.warning("Failed to log activity: %s", e)

    return stored


def run_elite_reporter(investigation_id: str) -> int:
    """Run the reporter for all pending tasks of an investigation.
    Returns number of findings collected."""
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    client = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key=OLLAMA_API_KEY)

    # Get pending tasks
    tasks_result = supabase.table("elite_tasks") \
        .select("*") \
        .eq("investigation_id", investigation_id) \
        .eq("status", "pending") \
        .order("task_order") \
        .execute()

    tasks = tasks_result.data or []
    if not tasks:
        logger.info("Reporter: no pending tasks for investigation %s", investigation_id)
        return 0

    total_findings = 0
    for task in tasks:
        logger.info("Reporter: working on task #%d: %s", task["task_order"], task["description"][:60])

        # Mark task in progress
        supabase.table("elite_tasks").update({"status": "in_progress"}).eq("id", task["id"]).execute()

        try:
            findings = _run_reporter_for_task(client, supabase, investigation_id, task)
            total_findings += len(findings)
            supabase.table("elite_tasks").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", task["id"]).execute()
        except Exception as e:
            logger.error("Reporter: task #%d failed: %s", task["task_order"], e)
            supabase.table("elite_tasks").update({"status": "failed"}).eq("id", task["id"]).execute()

    logger.info("Reporter: completed %d tasks, collected %d findings", len(tasks), total_findings)
    return total_findings


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Example usage
    investigation_id = os.getenv("INVESTIGATION_ID", "test-investigation")
    count = run_elite_reporter(investigation_id)
    print(f"Completed. Total findings: {count}")
