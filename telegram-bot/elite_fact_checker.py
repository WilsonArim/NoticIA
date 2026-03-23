"""
Elite Fact-Checker Forense — Verificação Adversarial
=====================================================
Guardião da veracidade. Opera com perfil "Confiança Zero".
Objectivo: escrutinar e tentar INVALIDAR o trabalho do Reporter.
Pesquisa INDEPENDENTE — nunca usa a mesma fonte do Reporter.

Poder de veto: pode rejeitar secções inteiras.
Threshold: fc_confidence >= 0.80 para publicação.
"""
import os
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional, Dict, List, Any

import httpx
from supabase import create_client
from openai import OpenAI

logger = logging.getLogger("elite.fact_checker")

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL = os.getenv("MODEL_ELITE_FC", os.getenv("MODEL_FACTCHECKER", "deepseek-v3.2"))
MODEL_VERDICT = os.getenv("MODEL_FC_VERDICT", MODEL)  # Non-reasoning model for JSON verdict
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

FC_CONFIDENCE_THRESHOLD = 0.80
TIMEOUT_SECONDS = 30
MAX_SEARCH_RESULTS = 5


# =============================================================================
# SEARCH IMPLEMENTATIONS
# =============================================================================

def _search_tavily(query: str, days: int = 7, exclude_url: Optional[str] = None) -> dict:
    """
    Tavily deep web search with optional URL exclusion.
    Returns findings with source credibility scoring.
    """
    if not TAVILY_API_KEY:
        return {"results": [], "error": "TAVILY_API_KEY not set"}

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "include_answer": True,
                "max_results": MAX_SEARCH_RESULTS,
                "days": days,
                "include_sources": True,
            }

            response = client.post(
                "https://api.tavily.com/search",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            # Filter results if exclude_url provided (avoid reporter's original source)
            results = data.get("results", [])
            if exclude_url:
                exclude_domain = urlparse(exclude_url).netloc.lower()
                filtered = [r for r in results if urlparse(r.get("url", "")).netloc.lower() != exclude_domain]
                if len(filtered) < len(results):
                    logger.info("Filtered out %d results from reporter's original domain", len(results) - len(filtered))
                results = filtered

            return {
                "query": query,
                "results": results[:MAX_SEARCH_RESULTS],
                "answer": data.get("answer", ""),
                "source": "tavily",
            }
    except Exception as e:
        logger.error("Tavily search failed: %s", e)
        return {"results": [], "error": str(e), "source": "tavily"}


def _search_serper(query: str, exclude_url: Optional[str] = None) -> dict:
    """
    Google Search via Serper API.
    """
    if not SERPER_API_KEY:
        return {"results": [], "error": "SERPER_API_KEY not set"}

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            headers = {
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            }
            payload = {
                "q": query,
                "num": MAX_SEARCH_RESULTS,
            }

            response = client.post(
                "https://google.serper.dev/search",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", [])[:MAX_SEARCH_RESULTS]:
                results.append({
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "content": item.get("snippet", ""),
                })

            # Filter by domain if needed
            if exclude_url:
                exclude_domain = urlparse(exclude_url).netloc.lower()
                filtered = [r for r in results if urlparse(r.get("url", "")).netloc.lower() != exclude_domain]
                if len(filtered) < len(results):
                    logger.info("Filtered out %d Serper results from reporter's original domain", len(results) - len(filtered))
                results = filtered

            return {
                "query": query,
                "results": results,
                "source": "serper",
            }
    except Exception as e:
        logger.error("Serper search failed: %s", e)
        return {"results": [], "error": str(e), "source": "serper"}


def _search_serper_news(query: str, exclude_url: Optional[str] = None) -> dict:
    """
    Google News via Serper API.
    """
    if not SERPER_API_KEY:
        return {"results": [], "error": "SERPER_API_KEY not set"}

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            headers = {
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            }
            payload = {
                "q": query,
                "num": MAX_SEARCH_RESULTS,
                "type": "news",
            }

            response = client.post(
                "https://google.serper.dev/news",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("news", [])[:MAX_SEARCH_RESULTS]:
                results.append({
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "content": item.get("snippet", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", ""),
                })

            # Filter by domain if needed
            if exclude_url:
                exclude_domain = urlparse(exclude_url).netloc.lower()
                filtered = [r for r in results if urlparse(r.get("url", "")).netloc.lower() != exclude_domain]
                if len(filtered) < len(results):
                    logger.info("Filtered out %d news results from reporter's original domain", len(results) - len(filtered))
                results = filtered

            return {
                "query": query,
                "results": results,
                "source": "serper_news",
            }
    except Exception as e:
        logger.error("Serper news search failed: %s", e)
        return {"results": [], "error": str(e), "source": "serper_news"}


def _search_exa(query: str, exclude_url: Optional[str] = None) -> dict:
    """
    Exa semantic search for academic/technical sources.
    """
    if not EXA_API_KEY:
        return {"results": [], "error": "EXA_API_KEY not set"}

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            headers = {
                "x-api-key": EXA_API_KEY,
                "Content-Type": "application/json",
            }
            payload = {
                "query": query,
                "numResults": MAX_SEARCH_RESULTS,
                "type": "auto",
                "useAutoprompt": True,
            }

            response = client.post(
                "https://api.exa.ai/search",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", [])[:MAX_SEARCH_RESULTS]:
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "content": item.get("text", ""),
                    "published_date": item.get("publishedDate", ""),
                    "author": item.get("author", ""),
                })

            # Filter by domain if needed
            if exclude_url:
                exclude_domain = urlparse(exclude_url).netloc.lower()
                filtered = [r for r in results if urlparse(r.get("url", "")).netloc.lower() != exclude_domain]
                if len(filtered) < len(results):
                    logger.info("Filtered out %d Exa results from reporter's original domain", len(results) - len(filtered))
                results = filtered

            return {
                "query": query,
                "results": results,
                "source": "exa",
            }
    except Exception as e:
        logger.error("Exa search failed: %s", e)
        return {"results": [], "error": str(e), "source": "exa"}


# =============================================================================
# OLLAMA WEB SEARCH
# =============================================================================

def _search_ollama(query: str, exclude_url: Optional[str] = None) -> dict:
    """
    Ollama Web Search — primary search provider (free, no bias, multilingual).
    """
    if not OLLAMA_BASE_URL or not OLLAMA_API_KEY:
        return {"results": [], "error": "OLLAMA credentials not set", "source": "ollama"}

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{OLLAMA_BASE_URL}/api/web_search",
                headers={"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"},
                json={"query": query, "max_results": MAX_SEARCH_RESULTS},
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", [])[:MAX_SEARCH_RESULTS]:
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "content": item.get("content", "")[:500],
                })

            # Filter by domain if needed
            if exclude_url:
                exclude_domain = urlparse(exclude_url).netloc.lower()
                filtered = [r for r in results if urlparse(r.get("url", "")).netloc.lower() != exclude_domain]
                if len(filtered) < len(results):
                    logger.info("Filtered out %d Ollama results from reporter domain", len(results) - len(filtered))
                results = filtered

            return {
                "query": query,
                "results": results,
                "source": "ollama",
            }
    except Exception as e:
        logger.error("Ollama search failed: %s", e)
        return {"results": [], "error": str(e), "source": "ollama"}


# =============================================================================
# TOOLS FOR LLM
# =============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ollama_search",
            "description": "Primary web search (multilingual, no bias). Use as your FIRST search tool. Returns results from diverse global sources in any language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query in any language — try adversarial queries",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "Deep web search. Use to find INDEPENDENT sources that either CONFIRM or CONTRADICT the fact being verified. Look for counter-evidence and alternative narratives.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — try adversarial queries like 'X denies' or 'X controversy'",
                    },
                    "days": {
                        "type": "integer",
                        "default": 7,
                        "description": "Days back to search",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "serper_search",
            "description": "Google Search. Use to find alternative coverage and broader context. Look for different perspectives on the same story.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "serper_news",
            "description": "Google News search. Use to find alternative media coverage and counter-narratives. Check if other outlets report the story differently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for news",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "exa_search",
            "description": "Semantic search for academic and technical sources. Use to verify technical claims or find expert analysis that may contradict the reported facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for academic/technical sources",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


SYSTEM_PROMPT = """You are the Elite Forensic Fact-Checker for NoticIA — an adversarial verification agent.

FUNDAMENTAL PRINCIPLE: ZERO TRUST — ADVERSARIAL VERIFICATION

Your job is to DESTROY the Reporter's work. Every claim is GUILTY until proven by independent evidence.

RULES:

1. INDEPENDENT SEARCH: When verifying a fact from the Reporter, NEVER use the same source they used. Find a DIFFERENT independent source. If you can only find the same original source, mark as "single_source" and penalize confidence by 40%.

2. MANDATORY COUNTER-NARRATIVE: For each major claim, ACTIVELY search for the opposite version. If Reporter says "company X smuggled chips", search for "company X denies accusations" or "company X defense". Record BOTH versions.

3. BIAS DETECTION IN SOURCES:
   - If ALL sources come from the same political/geographic side, mark as "selection_bias"
   - If a source uses emotional language ("terrible", "heroic", "disastrous"), discount authority by 30%
   - If a source cites "anonymous sources" without corroboration, max confidence is 0.50
   - Check publication date: very old sources (>2 years) get 20% discount unless they are primary/official documents

4. STATE PROPAGANDA & GEOPOLITICAL BALANCE: When the topic involves geopolitics:
   - Official version from country A (e.g., DOJ press release)
   - Official version from country B (e.g., Chinese Foreign Ministry statement)
   - At least 1 independent source from country C (neutral media)
   If only one side's version exists, mark section as "unilateral_narrative" and penalize confidence by 40%.

5. PRIMARY vs SECONDARY SOURCES:
   - Level 1 PRIMARY: Official documents (SEC filings, DOJ press releases, government records), court documents, peer-reviewed studies
   - Level 2 SECONDARY: Major established news outlets (Reuters, AP, Bloomberg, BBC)
   - Level 3 TERTIARY: Specialist publications, industry analysis, blogs
   - Level 4 QUATERNARY: Social media, unverified forums, anonymous sources

6. FACTS vs NARRATIVE: ALWAYS separate objective fact from interpretation:
   - FACT: "DOJ charged 3 SMCI executives on 2026-03-20" ✓
   - NARRATIVE: "This proves China is stealing technology" ✗

7. CONFIDENCE SCORING (0.0 to 1.0):
   - 0.90-1.00: Confirmed by 2+ Level 1 primary sources independently
   - 0.80-0.89: Confirmed by 1 Level 1 + 1 Level 2-3 source
   - 0.60-0.79: Confirmed by Level 2-3 sources only, or single Level 1
   - 0.40-0.59: Only Level 4 sources, or anonymous sources, or light corroboration
   - 0.20-0.39: Disputed — conflicting evidence found
   - 0.00-0.19: Rejected — counter-evidence is stronger, or clearly fabricated

8. METHODOLOGY:
   - Search 3-4 times with different queries to avoid reporting bias
   - Try to find counter-narratives by searching for "X denies", "X refutes", "X clarifies"
   - Check dates carefully — ensure sources are recent and relevant
   - For each finding, cite specific URL and text excerpt

RESPONSE FORMAT - Return ONLY valid JSON (no markdown, no extra text):
{
  "fc_status": "verified|disputed|rejected|needs_more_research",
  "fc_confidence": 0.85,
  "fc_notes": "Verified by independent SEC filing (Level 1). Counter-narrative: company claims charges are politically motivated (Level 2 Reuters). Single source limitation: original finding only appeared in [domain], but independent confirmation found in [other sources].",
  "fc_independent_sources": ["https://url1.com", "https://url2.com"],
  "bias_flags": ["none", "selection_bias", "emotional_language", "anonymous_sources", "unilateral_narrative", "conflict_of_interest"],
  "source_breakdown": {
    "level_1_primary": ["SEC filing URL"],
    "level_2_secondary": ["Reuters URL"],
    "counter_narratives": ["Company defense URL"]
  }
}

CRITICAL: Output ONLY the JSON object. No markdown, no backticks, no explanation."""


# =============================================================================
# TOOL EXECUTION
# =============================================================================

def _execute_search(tool_name: str, args: dict, exclude_url: Optional[str] = None) -> dict:
    """
    Execute a search tool and return results.
    """
    query = args.get("query", "")
    days = args.get("days", 7)

    if not query:
        return {"error": "Empty query", "results": []}

    logger.info("FC executing search: %s(%s)", tool_name, query[:60])

    try:
        if tool_name == "ollama_search":
            return _search_ollama(query, exclude_url=exclude_url)
        elif tool_name == "tavily_search":
            return _search_tavily(query, days=days, exclude_url=exclude_url)
        elif tool_name == "serper_search":
            return _search_serper(query, exclude_url=exclude_url)
        elif tool_name == "serper_news":
            return _search_serper_news(query, exclude_url=exclude_url)
        elif tool_name == "exa_search":
            return _search_exa(query, exclude_url=exclude_url)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error("Search tool execution failed: %s", e)
        return {"error": str(e), "results": []}


def _extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from LLM response, handling markdown formatting.
    """
    if not text:
        return None

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in markdown backticks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find standalone JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return None


# =============================================================================
# FACT VERIFICATION
# =============================================================================

def _collect_search_evidence(client: OpenAI, finding: dict) -> List[Dict[str, Any]]:
    """
    Phase 1: Run tool-call rounds to collect search evidence.
    Returns a list of search results gathered across all rounds.

    Uses tool_choice="required" (round 0) and "auto" (rounds 1-3).
    Stops when the model produces no tool calls or max rounds reached.
    """
    user_msg = f"""VERIFY THIS CLAIM (from the Reporter):

CLAIM: {finding.get('fact_statement', 'N/A')}
REPORTER'S SOURCE: {finding.get('source_url', 'N/A')}
SOURCE TYPE: {finding.get('source_type', 'unknown')}

YOUR TASK:
1. Search for INDEPENDENT sources that confirm or contradict this claim
2. Do NOT use the reporter's source ({finding.get('source_url', '')})
3. Search for counter-narratives: try "X denies", "X refutes", "X clarifies"
4. Use at least 2-3 different search tools with varied queries"""

    messages = [
        {"role": "system", "content": "You are a forensic fact-checker. Use the search tools to find independent evidence about the claim. Search thoroughly with diverse queries."},
        {"role": "user", "content": user_msg},
    ]

    max_search_rounds = 4
    reporter_source_url = finding.get("source_url", "")
    all_evidence = []

    for round_num in range(max_search_rounds):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="required" if round_num < 1 else "auto",
                temperature=0.1,
                max_tokens=2000,
            )
        except Exception as e:
            logger.error("FC search phase failed (round %d): %s", round_num, e)
            break

        choice = response.choices[0]
        msg = choice.message

        # If no tool calls, search phase is done
        if not msg.tool_calls:
            logger.info("FC search phase: model stopped calling tools at round %d", round_num)
            break

        messages.append(msg)
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                tool_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_args = {"query": tc.function.arguments}

            logger.info("FC search (round %d): %s(%s)", round_num, tool_name, tool_args.get("query", "")[:60])

            result = _execute_search(tool_name, tool_args, exclude_url=reporter_source_url)

            # Collect evidence
            for r in result.get("results", []):
                all_evidence.append({
                    "provider": result.get("source", tool_name),
                    "query": tool_args.get("query", ""),
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:400],
                })

            result_str = json.dumps(result, ensure_ascii=False)[:6000]
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

    logger.info("FC search phase complete: %d evidence items collected", len(all_evidence))
    return all_evidence


def _generate_verdict(client: OpenAI, finding: dict, evidence: List[Dict[str, Any]]) -> dict:
    """
    Phase 2: Generate JSON verdict in a CLEAN conversation (no tool messages).
    Uses MODEL_VERDICT (non-reasoning) to avoid deepseek-v3.2 reasoning-token overhead.
    """
    # Build evidence summary as plain text
    evidence_text = ""
    if evidence:
        for idx, e in enumerate(evidence[:10], 1):  # Cap at 10 items
            evidence_text += f"\n{idx}. [{e.get('provider','')}] Query: \"{e.get('query','')}\"\n"
            evidence_text += f"   Title: {e.get('title','')}\n"
            evidence_text += f"   URL: {e.get('url','')}\n"
            evidence_text += f"   Excerpt: {e.get('content','')[:200]}\n"
    else:
        evidence_text = "\nNo independent evidence found from any search provider.\n"

    verdict_prompt = f"""You are the Elite Forensic Fact-Checker for NoticIA. Analyse the evidence below and produce a verdict.

CLAIM UNDER VERIFICATION:
{finding.get('fact_statement', 'N/A')}

REPORTER'S ORIGINAL SOURCE: {finding.get('source_url', 'N/A')}
SOURCE TYPE: {finding.get('source_type', 'unknown')}

INDEPENDENT EVIDENCE COLLECTED:
{evidence_text}

SCORING RULES:
- 0.90-1.00: Confirmed by 2+ Level 1 primary sources independently
- 0.80-0.89: Confirmed by 1 Level 1 + 1 Level 2-3 source
- 0.60-0.79: Confirmed by Level 2-3 sources only
- 0.40-0.59: Only Level 4 or anonymous sources
- 0.20-0.39: Disputed — conflicting evidence
- 0.00-0.19: Rejected — counter-evidence stronger

If no independent evidence was found, max confidence is 0.40 ("single_source" bias flag).

Return ONLY a valid JSON object (no markdown, no backticks, no explanation):
{{"fc_status": "verified|disputed|rejected|needs_more_research", "fc_confidence": 0.85, "fc_notes": "...", "fc_independent_sources": ["url1", "url2"], "bias_flags": ["none"], "source_breakdown": {{"level_1_primary": [], "level_2_secondary": [], "counter_narratives": []}}}}"""

    # Clean conversation — no tool messages in history
    messages = [
        {"role": "user", "content": verdict_prompt},
    ]

    logger.info("FC verdict phase: using model %s with %d evidence items", MODEL_VERDICT, len(evidence))

    # Try up to 3 times to get valid JSON
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL_VERDICT,
                messages=messages,
                temperature=0.1,
                max_tokens=4000,  # Non-reasoning model needs fewer tokens
            )
        except Exception as e:
            logger.error("FC verdict call failed (attempt %d): %s", attempt, e)
            continue

        content = response.choices[0].message.content
        if not content:
            logger.warning("FC verdict attempt %d: empty response", attempt)
            # Add nudge for next attempt
            messages.append({"role": "assistant", "content": ""})
            messages.append({"role": "user", "content": "You returned an empty response. Please return ONLY a JSON object with keys: fc_status, fc_confidence, fc_notes, fc_independent_sources, bias_flags."})
            continue

        verdict = _extract_json_from_response(content)
        if verdict and "fc_status" in verdict and "fc_confidence" in verdict:
            # Validate and clamp confidence
            if isinstance(verdict.get("fc_confidence"), (int, float)):
                verdict["fc_confidence"] = max(0.0, min(1.0, float(verdict["fc_confidence"])))
            else:
                verdict["fc_confidence"] = 0.0
            if not isinstance(verdict.get("bias_flags"), list):
                verdict["bias_flags"] = ["none"]

            logger.info("FC verdict: %s (confidence: %.2f)", verdict["fc_status"], verdict["fc_confidence"])
            return verdict

        # Not valid JSON — retry
        logger.warning("FC verdict attempt %d: invalid JSON, retrying", attempt)
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": "That was not valid JSON. Return ONLY a raw JSON object. No markdown. No explanation. Keys: fc_status, fc_confidence, fc_notes, fc_independent_sources, bias_flags."})

    logger.warning("FC could not produce valid JSON verdict after 3 attempts")
    return {
        "fc_status": "needs_more_research",
        "fc_confidence": 0.0,
        "fc_notes": "Fact-checker could not produce a definitive verdict. Manual review required.",
        "bias_flags": ["none"],
    }


def _verify_finding(client: OpenAI, finding: dict) -> dict:
    """
    Verify a single finding adversarially using two-phase architecture.

    Phase 1: Collect search evidence via tool calls (separate LLM conversation).
    Phase 2: Generate JSON verdict in a CLEAN conversation (no tool messages).

    This two-phase approach avoids the deepseek-v3.2/Ollama bug where the model
    returns empty responses when tool_choice="none" or when the conversation
    history contains tool-call messages.
    """
    # Phase 1: Collect evidence
    evidence = _collect_search_evidence(client, finding)

    # Phase 2: Generate verdict (clean conversation, no tools)
    verdict = _generate_verdict(client, finding, evidence)

    return verdict


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def run_elite_fact_checker(investigation_id: str) -> dict:
    """
    Run adversarial fact-checking on all unverified findings.

    Args:
        investigation_id: Investigation ID to process

    Returns:
        Stats dict with counts: {verified, disputed, rejected, needs_research}
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Supabase credentials not configured")
        return {"error": "Supabase not configured", "verified": 0, "disputed": 0, "rejected": 0, "needs_research": 0}

    if not OLLAMA_BASE_URL or not OLLAMA_API_KEY:
        logger.error("Ollama credentials not configured")
        return {"error": "Ollama not configured", "verified": 0, "disputed": 0, "rejected": 0, "needs_research": 0}

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    client = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key=OLLAMA_API_KEY)

    logger.info("FC: starting fact-checking for investigation %s", investigation_id)

    # Get unverified findings
    try:
        result = supabase.table("elite_findings") \
            .select("*") \
            .eq("investigation_id", investigation_id) \
            .eq("fc_status", "unverified") \
            .execute()
        findings = result.data or []
    except Exception as e:
        logger.error("Failed to fetch findings: %s", e)
        return {"error": str(e), "verified": 0, "disputed": 0, "rejected": 0, "needs_research": 0}

    if not findings:
        logger.info("FC: no unverified findings for investigation %s", investigation_id)
        return {"verified": 0, "disputed": 0, "rejected": 0, "needs_research": 0}

    logger.info("FC: processing %d findings", len(findings))
    stats = {"verified": 0, "disputed": 0, "rejected": 0, "needs_research": 0}

    for idx, finding in enumerate(findings, 1):
        fact_statement = finding.get("fact_statement", "N/A")
        finding_id = finding.get("id", "unknown")

        # Check if reporter marked as unverifiable
        if "NÃO VERIFICADO" in fact_statement or finding.get("reporter_verified") == "NÃO VERIFICADO":
            logger.info("FC [%d/%d]: skipping unverifiable finding %s", idx, len(findings), finding_id)
            try:
                supabase.table("elite_findings").update({
                    "fc_status": "rejected",
                    "fc_confidence": 0.0,
                    "fc_notes": "Reporter declared unverifiable — no independent verification attempted",
                    "fc_checked_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", finding_id).execute()

                supabase.table("elite_activity_log").insert({
                    "investigation_id": investigation_id,
                    "agent": "fact_checker",
                    "action": "skipped_unverifiable",
                    "details": {
                        "finding_id": finding_id,
                        "fact": fact_statement[:100],
                    },
                }).execute()
            except Exception as e:
                logger.error("Failed to update finding %s: %s", finding_id, e)

            stats["rejected"] += 1
            continue

        logger.info("FC [%d/%d]: verifying %s", idx, len(findings), fact_statement[:80])

        # Run adversarial verification
        verdict = _verify_finding(client, finding)

        fc_status = verdict.get("fc_status", "needs_more_research")
        fc_confidence = float(verdict.get("fc_confidence", 0.0))
        fc_notes = verdict.get("fc_notes", "")[:2000]
        fc_sources = verdict.get("fc_independent_sources", [])
        bias_flags = verdict.get("bias_flags", ["none"])

        # Update stats
        if fc_status == "verified":
            stats["verified"] += 1
        elif fc_status == "disputed":
            stats["disputed"] += 1
        elif fc_status == "rejected":
            stats["rejected"] += 1
        else:
            stats["needs_research"] += 1

        # Update finding in database
        try:
            supabase.table("elite_findings").update({
                "fc_status": fc_status,
                "fc_confidence": fc_confidence,
                "fc_notes": fc_notes,
                "fc_independent_sources": fc_sources,
                "fc_bias_flags": bias_flags,
                "fc_checked_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", finding_id).execute()

            logger.info("FC [%d/%d]: updated finding — status=%s confidence=%.2f", idx, len(findings), fc_status, fc_confidence)
        except Exception as e:
            logger.error("Failed to update finding %s: %s", finding_id, e)
            continue

        # Log activity
        try:
            supabase.table("elite_activity_log").insert({
                "investigation_id": investigation_id,
                "agent": "fact_checker",
                "action": "verified_finding",
                "details": {
                    "finding_id": finding_id,
                    "fact": fact_statement[:100],
                    "verdict": fc_status,
                    "confidence": fc_confidence,
                    "sources_found": len(fc_sources),
                },
            }).execute()
        except Exception as e:
            logger.error("Failed to log activity: %s", e)

    logger.info("FC: completed — verified=%d disputed=%d rejected=%d needs_research=%d",
                stats["verified"], stats["disputed"], stats["rejected"], stats["needs_research"])
    return stats


if __name__ == "__main__":
    # Example usage for testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Run fact-checker for a test investigation
    test_investigation_id = "test-investigation-001"
    result = run_elite_fact_checker(test_investigation_id)
    print(f"Fact-checker results: {result}")
