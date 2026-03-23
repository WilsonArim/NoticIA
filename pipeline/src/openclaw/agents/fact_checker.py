"""
Agente Fact-Checker — Nemotron 3 Super (120B, tool calling nativo)
Verifica evidência REAL. Bias baseado em suporte factual, não linguagem.

Lê status='auditor_approved', escreve:
- status='approved' (certainty >= 0.70, bias baseado em evidência)
- status='fact_check' (rejeitado: sem fontes, falso, ou demasiado antigo)

Pesquisa: Ollama (primário) → Serper.dev → Tavily → Exa.ai (último recurso)
Artigos normais: 1 pesquisa composta | Artigos dossiê: 3 pesquisas dirigidas
"""
import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta

import httpx
from supabase import create_client

from openclaw.agents.ollama_client import chat_with_tools

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL = os.getenv("MODEL_FACTCHECKER", "nemotron-3-super:cloud")
BATCH_SIZE = int(os.getenv("FACTCHECKER_BATCH_SIZE", "10"))
MAX_EVENT_AGE_DAYS = int(os.getenv("MAX_EVENT_AGE_DAYS", "7"))


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
    """Pesquisa real com fallback automático: Ollama → Serper → Tavily → Exa."""

    # 0. Ollama Web Search (primário — gratuito, sem viés, multilíngue)
    if OLLAMA_API_KEY and OLLAMA_BASE_URL:
        try:
            resp = httpx.post(
                f"{OLLAMA_BASE_URL}/api/web_search",
                headers={"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"},
                json={"query": query, "max_results": 7},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                logger.debug("Search via Ollama: %d resultados", len(results))
                return {
                    "provider": "ollama",
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "description": r.get("content", "")[:500],
                        }
                        for r in results[:7]
                    ],
                }
        except Exception as e:
            logger.warning("Ollama Web Search falhou: %s — tentando Serper.dev", e)

    # 1. Serper.dev (secundário — Google results, rápido)
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
                logger.debug("Search via Serper (Google): %d resultados", len(organic))
                return {
                    "provider": "serper_google",
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
            logger.warning("Serper.dev falhou: %s — tentando Tavily", e)

    # 2. Tavily (terciário — melhor para fact-checking, sem viés conhecido)
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
                    "days": 30,  # apenas resultados dos últimos 30 dias
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

    # 3. Exa.ai (último recurso — cobertura técnica e académica)

    return {
        "error": (
            "Nenhum provider de pesquisa disponível. "
            "Configura TAVILY_API_KEY, EXA_API_KEY ou SERPER_API_KEY em pipeline/.env"
        )
    }


# ── Agente principal ────────────────────────────────────────────────────


def run_fact_checker():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # --- pipeline_runs logging: início ---
    run_id = None
    try:
        run_row = supabase.table("pipeline_runs").insert({
            "stage": "fact_checker",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events_in": 0,
            "events_out": 0,
        }).execute()
        run_id = run_row.data[0]["id"] if run_row.data else None
    except Exception as e:
        logger.warning("Fact-checker: falha ao criar pipeline_run: %s", e)

    result = (
        supabase.table("intake_queue")
        .select("*")
        .eq("status", "auditor_approved")
        .order("score", desc=True)
        .limit(BATCH_SIZE)
        .execute()
    )

    items = result.data or []

    # Filtrar áreas desactivadas (desporto)
    DISABLED_AREAS = {"desporto", "sports", "sport"}
    filtered_items = []
    for item in items:
        area = (item.get("area") or "").lower()
        if area in DISABLED_AREAS:
            supabase.table("intake_queue").update({
                "status": "fact_check",
                "error_message": f"Área '{area}' desactivada editorialmente",
            }).eq("id", item["id"]).execute()
            logger.info("Fact-checker: REJEITADO (área desactivada) '%s'", item.get("title", "")[:50])
            continue
        filtered_items.append(item)
    items = filtered_items

    if not items:
        logger.info("Fact-checker: sem items para verificar")
        # --- pipeline_runs logging: fim (sem items) ---
        if run_id:
            try:
                supabase.table("pipeline_runs").update({
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "events_in": 0, "events_out": 0,
                }).eq("id", run_id).execute()
            except Exception:
                pass
        return

    logger.info("Fact-checker: verificando %d items com %s", len(items), MODEL)
    approved_count = 0

    for item in items:
        try:
            verdict = _check_item(item)
            _apply_verdict(supabase, item, verdict)
            if verdict.get("aprovado") and float(verdict.get("certainty_score", 0)) >= 0.70:
                approved_count += 1
        except Exception as e:
            logger.error("Fact-checker erro item %s: %s", item["id"], e)

    # --- pipeline_runs logging: fim ---
    if run_id:
        try:
            supabase.table("pipeline_runs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": len(items),
                "events_out": approved_count,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Fact-checker: falha ao actualizar pipeline_run: %s", e)


def _check_item(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    is_dossie = metadata.get("source_agent") == "dossie"
    n_searches = 3 if is_dossie else 1
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system = f"""És um fact-checker jornalístico rigoroso. A tua missão é verificar factos com pesquisa real.
Hoje é {hoje}.

REGRAS FUNDAMENTAIS:
1. Bias NÃO é medido por linguagem forte. É medido por suporte factual.
   - "O Irão executa cidadãos" → pesquisa → confirma com dados reais → bias BAIXO
   - "X aconteceu" → pesquisa → nenhuma fonte confirma → bias ALTO (afirmação sem suporte)
2. Usa web_search para verificar as afirmações principais do artigo.
   - Este artigo {"É de dossiê investigativo: faz EXATAMENTE 3 pesquisas dirigidas, uma por afirmação principal." if is_dossie else "é um artigo normal: faz 1 pesquisa composta que cubra as afirmações principais."}
3. Procura sempre fontes primárias: relatórios oficiais, dados governamentais, ONG credenciadas (HRW, Amnesty, FATF, UN, bancos centrais).
4. Uma notícia que a imprensa mainstream ignora NÃO é falsa por isso. Verifica com fontes primárias.
5. Se o resultado da pesquisa vier de provider "serper_google", lê o campo "warning" e aplica o aviso — desvaloriza media mainstream.
6. DATAS DAS FONTES — CRÍTICO: Inclui em "fontes_encontradas" APENAS URLs que cobrem o evento ACTUAL.
   - Um artigo da BBC de 2022 sobre "Zelenskyy no Parlamento" NÃO verifica um evento de {hoje}.
   - Se encontrares cobertura de evento semanticamente similar mas de outro ano, IGNORA essa fonte.
   - Inclui SEMPRE o ano de {hoje[:4]} nas tuas queries de pesquisa para forçar resultados recentes.
7. Responde sempre em JSON válido no final.
8. SCORING GRANULAR — OBRIGATÓRIO: Os teus scores (certainty_score, bias_score) devem reflectir a avaliação EXACTA deste artigo. NUNCA uses múltiplos de 0.05 (como 0.90, 0.85, 0.10, 0.15). Usa valores precisos como 0.87, 0.93, 0.11, 0.08. Cada artigo é único — os seus scores devem ser únicos."""

    user = f"""Verifica este artigo com pesquisa real:

TÍTULO: {item.get("title", "")}
CONTEÚDO: {item.get("content", "")[:1000]}
FONTE ORIGINAL: {item.get("url", "")}
DATA: {item.get("received_at", "desconhecida")}
TIPO: {"DOSSIÊ INVESTIGATIVO — requer 3 pesquisas dirigidas" if is_dossie else "Artigo normal — 1 pesquisa composta suficiente"}

PROCESSO:
1. Identifica as {n_searches} afirmações {"mais importantes, uma por pesquisa" if is_dossie else "principais e formula 1 query composta"}
2. {"Faz 1 web_search por afirmação (total: 3 chamadas)" if is_dossie else "Faz 1 web_search com query composta em inglês"}
3. Avalia com GRANULARIDADE (usa decimais exactos, NUNCA multiplos de 0.05):

   certainty_score — baseado na qualidade e quantidade de fontes:
   - 0.96-1.00: 3+ fontes primárias oficiais independentes confirmam (raríssimo)
   - 0.91-0.95: 2 fontes primárias + contexto confirma
   - 0.86-0.90: 1 fonte primária + 1-2 fontes secundárias
   - 0.80-0.85: Fontes secundárias apenas (agências, media credível)
   - 0.70-0.79: 1 fonte credível sem corroboração
   - <0.70: Não aprovado

   bias_score — baseado em desvio factual (0.0=neutro perfeito):
   - 0.01-0.06: Factos puros, sem adjectivação, múltiplas perspectivas
   - 0.07-0.12: Ligeiro enquadramento editorial, factos correctos
   - 0.13-0.19: Perspectiva dominante mas factos suportados
   - 0.20-0.30: Viés evidente, omissão de contra-argumentos
   - >0.30: Propaganda ou desinformação

   IMPORTANTE: Calcula o score EXACTO para este artigo específico. Cada artigo é diferente.
   Exemplos: 0.87, 0.93, 0.11, 0.08, 0.14 — NUNCA uses 0.90, 0.95, 0.10, 0.05, 0.85.
   
   - frescura (o evento aconteceu nos últimos 7 dias? se não, nota a data real)
4. Devolve JSON final:

{{
  "aprovado": true,
  "certainty_score": 0.87,
  "bias_score": 0.08,
  "veracidade": "confirmado",
  "fontes_encontradas": ["url1", "url2"],
  "data_real_evento": "2026-03-15",
  "notas": "Confirmado por relatório FATF 2025 e dados do Banco Central. Certainty 0.87 porque fonte primária (FATF) confirma directamente + 1 fonte secundária (Reuters). Bias 0.08 porque enquadramento é factual mas inclui ligeira ênfase editorial no título."
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


def _extract_year_from_url(url: str) -> int | None:
    """Extrai o ano de publicação de um URL se estiver embutido no path."""
    patterns = [
        r"/(\d{4})/\d{2}/\d{2}/",   # /YYYY/MM/DD/
        r"/(\d{4})/\d{2}/",          # /YYYY/MM/
        r"/(\d{4})/[^/]",            # /YYYY/slug
        r"-(\d{4})\d{4}",            # -YYYYMMDD
        r"_(\d{4})\d{4}",            # _YYYYMMDD
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            year = int(m.group(1))
            if 2000 <= year <= 2100:
                return year
    return None


def _filter_stale_sources(
    fontes: list[str], data_real_str: str | None
) -> tuple[list[str], list[str]]:
    """Remove fontes cujo URL contém um ano diferente do evento.

    Retorna (fontes_válidas, fontes_rejeitadas).
    """
    if not data_real_str or len(str(data_real_str)) < 4:
        return fontes, []
    try:
        evento_year = int(str(data_real_str)[:4])
    except ValueError:
        return fontes, []

    validas: list[str] = []
    rejeitadas: list[str] = []
    for url in fontes:
        url_year = _extract_year_from_url(url)
        if url_year is not None and url_year != evento_year:
            rejeitadas.append(url)
            logger.warning(
                "Fonte rejeitada (ano URL %d ≠ evento %d): %s",
                url_year, evento_year, url,
            )
        else:
            validas.append(url)
    return validas, rejeitadas


def _event_is_stale(data_real_str: str | None) -> tuple[bool, str]:
    """Verifica deterministicamente se o evento é demasiado antigo."""
    if not data_real_str or len(str(data_real_str)) < 10:
        return False, ""
    try:
        evento_date = datetime.strptime(str(data_real_str)[:10], "%Y-%m-%d").date()
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=MAX_EVENT_AGE_DAYS)
        if evento_date < cutoff:
            return True, f"stale_event: data real do evento é {data_real_str} (>{MAX_EVENT_AGE_DAYS} dias)"
    except ValueError:
        pass
    return False, ""


def _apply_verdict(supabase, item: dict, verdict: dict):
    certainty = float(verdict.get("certainty_score", 0.0))
    bias = float(verdict.get("bias_score", 0.5))
    data_real = verdict.get("data_real_evento")

    # ── Check determinístico de frescura com a data confirmada pelo fact-checker ──
    stale, motivo_stale = _event_is_stale(data_real)
    if stale:
        supabase.table("intake_queue").update({
            "status": "fact_check",
            "error_message": motivo_stale,
            "fact_check_summary": {
                "certainty_score": 0.0,
                "veracidade": "stale",
                "data_real_evento": data_real,
                "notas": motivo_stale,
            },
        }).eq("id", item["id"]).execute()
        logger.warning("Fact-checker: STALE '%s' — %s", item.get("title", "")[:50], motivo_stale)
        return

    aprovado = verdict.get("aprovado", False) and certainty >= 0.70

    # ── Filtrar fontes com ano errado no URL ──────────────────────────────
    fontes_raw = verdict.get("fontes_encontradas", [])
    fontes_validas, fontes_rejeitadas = _filter_stale_sources(fontes_raw, data_real)
    if fontes_rejeitadas:
        logger.warning(
            "Fact-checker: %d fonte(s) rejeitada(s) por ano incorreto: %s",
            len(fontes_rejeitadas), fontes_rejeitadas,
        )

    fact_check_summary = {
        "certainty_score": certainty,
        "veracidade": verdict.get("veracidade", ""),
        "fontes_encontradas": fontes_validas,
        "fontes_rejeitadas_ano": fontes_rejeitadas,
        "data_real_evento": data_real,
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
        "Fact-checker: '%s' → %s (cert=%.2f, bias=%.2f, data=%s)",
        item.get("title", "")[:50],
        "APROVADO" if aprovado else "REJEITADO",
        certainty,
        bias,
        data_real or "desconhecida",
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_fact_checker()
