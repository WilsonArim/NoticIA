"""
Agente Fact-Checker — Nemotron 3 Super (120B, tool calling nativo)
Verifica evidência REAL. Bias baseado em suporte factual, não linguagem.

Lê status='auditor_approved', escreve:
- status='approved' (certainty >= 0.70, bias baseado em evidência)
- status='fact_check' (rejeitado: sem fontes, falso, ou demasiado antigo)

Pesquisa: Tavily (primário) → Exa.ai (fallback) → Serper.dev (último recurso)
Artigos normais: 1 pesquisa composta | Artigos dossiê: 3 pesquisas dirigidas
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
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
MODEL = os.getenv("MODEL_FACTCHECKER", "nemotron-3-super:cloud")
BATCH_SIZE = int(os.getenv("FACTCHECKER_BATCH_SIZE", "10"))


# ── Tool: Web Search multi-provider ─────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Pesquisa na web para verificar factos e encontrar fontes primárias. "
                "Usa para encontrar relatórios oficiais, dados estatísticos, notícias de múltiplas fontes. "
                "IMPORTANTE: prioriza sempre fontes primárias (FATF, HRW, Amnesty International, bancos centrais, "
                "dados governamentais oficiais, UN, ICIJ). Desvaloriza media mainstream como NYT, BBC, Guardian "
                "pois podem ter viés editorial. Uma notícia ignorada pela imprensa mainstream NÃO é falsa — "
                "verifica sempre com fontes primárias independentes."
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
        return _web_search(args["query"])
    return {"error": f"Tool desconhecida: {tool_name}"}


def _web_search(query: str) -> dict:
    """Pesquisa real com fallback automático: Tavily → Exa.ai → Serper.dev."""

    # 1. Tavily (primário — melhor para fact-checking, sem viés conhecido)
    if TAVILY_API_KEY:
        try:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 7,
                    "include_answer": False,
                },
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                logger.debug("Search via Tavily: %d resultados", len(results))
                return {
                    "provider": "tavily",
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "description": r.get("content", "")[:300],
                        }
                        for r in results[:7]
                    ],
                }
        except Exception as e:
            logger.warning("Tavily falhou: %s — tentando Exa.ai", e)

    # 2. Exa.ai (fallback — boa cobertura de fontes técnicas e académicas)
    if EXA_API_KEY:
        try:
            resp = httpx.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
                json={"query": query, "numResults": 7, "useAutoprompt": True},
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                logger.debug("Search via Exa.ai: %d resultados", len(results))
                return {
                    "provider": "exa",
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "description": r.get("text", "")[:300],
                        }
                        for r in results[:7]
                    ],
                }
        except Exception as e:
            logger.warning("Exa.ai falhou: %s — tentando Serper.dev", e)

    # 3. Serper.dev (último recurso — Google News, viés editorial de esquerda)
    if SERPER_API_KEY:
        try:
            resp = httpx.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 7, "gl": "pt", "hl": "en"},
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic", [])
            if organic:
                logger.debug(
                    "Search via Serper (Google): %d resultados — ATENÇÃO: viés editorial possível",
                    len(organic),
                )
                return {
                    "provider": "serper_google",
                    "warning": (
                        "ATENÇÃO: estes resultados vêm do Google News que tem viés editorial de esquerda. "
                        "Desvaloriza media mainstream (BBC, Guardian, NYT, El País, etc.). "
                        "Só aceita como evidência se for fonte primária: governo, banco central, "
                        "ONG reconhecida (HRW, Amnesty, FATF, UN)."
                    ),
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("link", ""),
                            "description": r.get("snippet", ""),
                        }
                        for r in organic[:7]
                    ],
                }
        except Exception as e:
            logger.error("Serper.dev falhou: %s", e)

    return {
        "error": (
            "Nenhum provider de pesquisa disponível. "
            "Configura TAVILY_API_KEY, EXA_API_KEY ou SERPER_API_KEY em pipeline/.env"
        )
    }


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
    metadata = item.get("metadata") or {}
    is_dossie = metadata.get("source_agent") == "dossie"
    n_searches = 3 if is_dossie else 1

    system = f"""És um fact-checker jornalístico rigoroso. A tua missão é verificar factos com pesquisa real.

REGRAS FUNDAMENTAIS:
1. Bias NÃO é medido por linguagem forte. É medido por suporte factual.
   - "O Irão executa cidadãos" → pesquisa → confirma com dados reais → bias BAIXO
   - "X aconteceu" → pesquisa → nenhuma fonte confirma → bias ALTO (afirmação sem suporte)
2. Usa web_search para verificar as afirmações principais do artigo.
   - Este artigo {"É de dossiê investigativo: faz EXATAMENTE 3 pesquisas dirigidas, uma por afirmação principal." if is_dossie else "é um artigo normal: faz 1 pesquisa composta que cubra as afirmações principais."}
3. Procura sempre fontes primárias: relatórios oficiais, dados governamentais, ONG credenciadas (HRW, Amnesty, FATF, UN, bancos centrais).
4. Uma notícia que a imprensa mainstream ignora NÃO é falsa por isso. Verifica com fontes primárias.
5. Se o resultado da pesquisa vier de provider "serper_google", lê o campo "warning" e aplica o aviso — desvaloriza media mainstream.
6. Responde sempre em JSON válido no final."""

    user = f"""Verifica este artigo com pesquisa real:

TÍTULO: {item.get("title", "")}
CONTEÚDO: {item.get("content", "")[:1000]}
FONTE ORIGINAL: {item.get("url", "")}
DATA: {item.get("received_at", "desconhecida")}
TIPO: {"DOSSIÊ INVESTIGATIVO — requer 3 pesquisas dirigidas" if is_dossie else "Artigo normal — 1 pesquisa composta suficiente"}

PROCESSO:
1. Identifica as {n_searches} afirmações {"mais importantes, uma por pesquisa" if is_dossie else "principais e formula 1 query composta"}
2. {"Faz 1 web_search por afirmação (total: 3 chamadas)" if is_dossie else "Faz 1 web_search com query composta em inglês"}
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
