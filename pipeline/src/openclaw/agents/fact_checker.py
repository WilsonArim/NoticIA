"""
Agente Fact-Checker — Nemotron 3 Super (120B, tool calling nativo)
Verifica evidência REAL. Bias baseado em suporte factual, não linguagem.

Lê status='auditor_approved', escreve:
- status='approved' (certainty >= 0.70, bias baseado em evidência)
- status='fact_check' (rejeitado: sem fontes, falso, ou demasiado antigo)
"""
import os
import json
import logging

import httpx
from supabase import create_client

from openclaw.agents.ollama_client import chat_with_tools

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
MODEL = os.getenv("MODEL_FACTCHECKER", "nemotron-3-super:cloud")
BATCH_SIZE = int(os.getenv("FACTCHECKER_BATCH_SIZE", "10"))


# ── Tool: Web Search via Brave API ──────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Pesquisa na web para verificar factos e encontrar fontes primárias. "
                "Usa para encontrar relatórios oficiais, dados estatísticos, notícias de múltiplas fontes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query de pesquisa em inglês para melhores resultados",
                    },
                    "focus": {
                        "type": "string",
                        "enum": ["facts", "statistics", "official_reports", "news"],
                        "description": "Tipo de resultado pretendido",
                    },
                },
                "required": ["query"],
            },
        },
    }
]


def execute_tool(tool_name: str, args: dict) -> dict:
    if tool_name == "web_search":
        return _brave_search(args["query"])
    return {"error": f"Tool desconhecida: {tool_name}"}


def _brave_search(query: str) -> dict:
    """Pesquisa real via Brave Search API."""
    if not BRAVE_API_KEY:
        return {"warning": "BRAVE_API_KEY não configurada — instala em https://api.search.brave.com"}

    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY},
            params={"q": query, "count": 5, "search_lang": "en"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("web", {}).get("results", [])
        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                for r in results[:5]
            ]
        }
    except Exception as e:
        logger.error("Brave Search erro: %s", e)
        return {"error": str(e)}


# ── Agente principal ────────────────────────────────────────────────────


def run_fact_checker():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("intake_queue")
        .select("*")
        .eq("status", "auditor_approved")
        .order("score", desc=True)
        .limit(BATCH_SIZE)
        .execute()
    )

    items = result.data or []
    if not items:
        logger.info("Fact-checker: sem items para verificar")
        return

    logger.info("Fact-checker: verificando %d items com %s", len(items), MODEL)

    for item in items:
        try:
            verdict = _check_item(item)
            _apply_verdict(supabase, item, verdict)
        except Exception as e:
            logger.error("Fact-checker erro item %s: %s", item["id"], e)


def _check_item(item: dict) -> dict:
    system = """És um fact-checker jornalístico rigoroso. A tua missão é verificar factos com pesquisa real.

REGRAS FUNDAMENTAIS:
1. Bias NÃO é medido por linguagem forte. É medido por suporte factual.
   - "O Irão executa cidadãos" → pesquisa → confirma com dados reais → bias BAIXO
   - "X aconteceu" → pesquisa → nenhuma fonte confirma → bias ALTO (afirmação sem suporte)
2. Usa web_search para verificar as afirmações principais do artigo.
3. Procura sempre fontes primárias: relatórios oficiais, dados governamentais, ONG credenciadas (HRW, Amnesty, FATF, UN, bancos centrais).
4. Uma notícia que a imprensa mainstream ignora NÃO é falsa por isso. Verifica com fontes primárias.
5. Responde sempre em JSON válido no final."""

    user = f"""Verifica este artigo com pesquisa real:

TÍTULO: {item.get("title", "")}
CONTEÚDO: {item.get("content", "")[:1000]}
FONTE ORIGINAL: {item.get("url", "")}
DATA: {item.get("received_at", "desconhecida")}

PROCESSO:
1. Identifica as 2-3 afirmações principais
2. Pesquisa cada uma com web_search (usa inglês para melhores resultados)
3. Avalia:
   - veracidade (0.0=falso, 0.5=meia-verdade, 1.0=confirmado por fontes primárias)
   - bias (0.0=neutro/baseado em factos, 1.0=sem suporte factual ou propaganda)
   - frescura (o evento aconteceu nos últimos 7 dias? se não, nota a data real)
4. Devolve JSON final:

{{
  "aprovado": true,
  "certainty_score": 0.85,
  "bias_score": 0.10,
  "veracidade": "confirmado",
  "fontes_encontradas": ["url1", "url2"],
  "data_real_evento": "2026-03-15",
  "notas": "Confirmado por relatório FATF 2025 e dados do Banco Central"
}}"""

    response = chat_with_tools(
        model=MODEL,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    return {"aprovado": False, "certainty_score": 0.0, "notas": "Falha a parsear resposta"}


def _apply_verdict(supabase, item: dict, verdict: dict):
    certainty = float(verdict.get("certainty_score", 0.0))
    bias = float(verdict.get("bias_score", 0.5))
    aprovado = verdict.get("aprovado", False) and certainty >= 0.70

    fact_check_summary = {
        "certainty_score": certainty,
        "veracidade": verdict.get("veracidade", ""),
        "fontes_encontradas": verdict.get("fontes_encontradas", []),
        "data_real_evento": verdict.get("data_real_evento"),
        "notas": verdict.get("notas", ""),
    }

    bias_analysis = {
        "score": bias,
        "method": "evidence-based",
        "model": MODEL,
    }

    update: dict = {
        "status": "approved" if aprovado else "fact_check",
        "fact_check_summary": fact_check_summary,
        "bias_score": bias,
        "bias_analysis": bias_analysis,
    }

    if not aprovado:
        update["error_message"] = verdict.get("notas", "Fact-check falhou")

    supabase.table("intake_queue").update(update).eq("id", item["id"]).execute()

    logger.info(
        "Fact-checker: '%s' → %s (cert=%.2f, bias=%.2f)",
        item.get("title", "")[:50],
        "APROVADO" if aprovado else "REJEITADO",
        certainty,
        bias,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_fact_checker()
