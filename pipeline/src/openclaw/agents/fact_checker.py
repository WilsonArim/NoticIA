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
    """V3 dual-mode fact-checker: routes by vertente."""
    vertente = item.get("vertente", "media_watch")

    if vertente == "media_watch":
        return _check_item_media_audit(item)
    elif vertente == "alt_news":
        return _check_item_alt_news(item)
    elif vertente == "editorial":
        return _check_item_editorial(item)
    else:
        return _check_item_media_audit(item)  # fallback


def _check_item_media_audit(item: dict) -> dict:
    """V3 MEDIA WATCH: Audit media honesty, framing, omissions."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system = f"""Es um auditor de media do NoticIA. A tua missao NAO e verificar se a noticia e verdade.
A tua missao e AUDITAR se os media contam a historia de forma COMPLETA e HONESTA.
Hoje e {hoje}.

REGRAS FUNDAMENTAIS:
1. Uma noticia pode ser factualmente correcta MAS ter vies por omissao, framing, ou seleccao de dados.
2. Procura SEMPRE o OUTRO LADO da historia com web_search.
3. Compara como DIFERENTES fontes cobrem o mesmo evento.
4. Procura dados PRIMARIOS (governos, institutos, ONG) que contradizem ou complementam a narrativa.
5. Uma noticia que omite factos relevantes e tao enviesada como uma que mente.

ANALISA:
1. FACTOS - Os dados apresentados sao correctos?
2. FRAMING - Linguagem carregada? Um lado e o "bom" e o outro o "mau"?
3. OMISSAO - Que factos relevantes faltam? Que contexto e omitido?
4. FONTES CITADAS - Quem e citado? Quem DEVERIA ser citado mas nao e?
5. DADOS vs NARRATIVA - Fontes primarias contradizem a narrativa?
6. COBERTURA ASSIMETRICA - Os media deram a este evento a atencao proporcional ao seu impacto?

USA web_search PARA:
- Procurar o OUTRO LADO da historia
- Procurar dados primarios/oficiais sobre o tema
- Procurar se outros media contam de forma diferente
- Procurar se fontes alternativas reportam factos omitidos

SCORING GRANULAR (NUNCA multiplos de 0.05):
certainty_score: confianca nos factos APRESENTADOS (pode ser alta mesmo com vies)
bias_score: grau de vies detectado (0.0=neutro, 1.0=propaganda)

DEVOLVE JSON:
{{
  "aprovado": true,
  "factos_correctos": true,
  "certainty_score": 0.XX,
  "bias_score": 0.XX,
  "bias_type": "none|framing|omission|selective_data|asymmetric|propaganda",
  "omitted_facts": ["facto omitido 1", "facto omitido 2"],
  "counter_narrative": "O que os media nao dizem e...",
  "veracidade": "confirmado|parcial|falso",
  "fontes_encontradas": ["url1", "url2"],
  "data_real_evento": "2026-03-XX",
  "publish_recommendation": "expose|omission|discard|needs_review",
  "notas": "Explicacao detalhada da auditoria"
}}

REGRAS DE publish_recommendation:
- "expose": vies significativo detectado (bias_score > 0.20) OU omissoes graves
- "omission": factos correctos MAS omissao significativa de contexto
- "discard": noticia factualmente correcta, sem vies significativo, sem omissoes — NAO nos interessa
- "needs_review": ambiguo, precisa de revisao humana"""

    user = f"""AUDITA esta noticia dos media:

TITULO: {item.get("title", "")}
CONTEUDO: {item.get("content", "")[:1200]}
FONTE ORIGINAL: {item.get("url", "")}
AREA: {item.get("area", "")}
DATA: {item.get("received_at", "desconhecida")}

PROCESSO:
1. Identifica as afirmacoes principais
2. Faz 1-2 web_search para encontrar o OUTRO LADO e dados primarios
3. Avalia honestidade, completude, e framing
4. Decide: expose, omission, discard, ou needs_review
5. Devolve JSON final"""

    response = chat_with_tools(
        model=MODEL,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    return _parse_fc_response(response)


def _check_item_alt_news(item: dict) -> dict:
    """V3 ALT-NEWS: Rigorous verification of alternative sources. Needs 3+ independent sources."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    metadata = item.get("metadata") or {}
    is_dossie = metadata.get("source_agent") == "dossie"
    n_searches = 3 if is_dossie else 2

    system = f"""Es um fact-checker rigoroso do NoticIA. Esta noticia vem de fonte ALTERNATIVA (Telegram, redes sociais).
Hoje e {hoje}.

REGRAS FUNDAMENTAIS — VERIFICACAO RIGOROSA:
1. Fontes alternativas precisam de verificacao EXTRA. Ha muita verdade mas tambem muito lixo.
2. Precisa de 3+ fontes INDEPENDENTES para aprovacao. Sem 3 fontes → rejeita (certainty < 0.70).
3. Procura SEMPRE fontes primarias: relatorios oficiais, dados governamentais, ONG credenciadas.
4. Uma noticia que a imprensa mainstream ignora NAO e falsa por isso. Verifica com fontes primarias.
5. Se o evento e real mas sem fontes suficientes, marca como needs_review (para Wilson verificar manualmente).

SCORING GRANULAR (NUNCA multiplos de 0.05):
certainty_score (threshold MAIS ALTO para alt-news):
- 0.93-1.00: 3+ fontes primarias independentes (aprovacao forte)
- 0.85-0.92: 2 fontes primarias + contexto confirma
- 0.70-0.84: 1 fonte credivel — aprovacao condicional
- <0.70: NAO APROVADO (fontes insuficientes)

bias_score: baseado em suporte factual (0.0=neutro):
- 0.01-0.10: Factos puros, bem documentados
- 0.11-0.20: Ligeiro enquadramento, factos correctos
- >0.20: Vies evidente ou sem suporte factual

Faz {n_searches} web_search para verificar as afirmacoes principais.

DEVOLVE JSON:
{{
  "aprovado": true/false,
  "certainty_score": 0.XX,
  "bias_score": 0.XX,
  "veracidade": "confirmado|parcial|nao_verificavel|falso",
  "fontes_encontradas": ["url1", "url2", "url3"],
  "data_real_evento": "2026-03-XX",
  "publish_recommendation": "alt_news|needs_review|discard",
  "notas": "..."
}}"""

    user = f"""VERIFICA RIGOROSAMENTE esta noticia de fonte alternativa:

TITULO: {item.get("title", "")}
CONTEUDO: {item.get("content", "")[:1200]}
FONTE: {item.get("url", "")}
AREA: {item.get("area", "")}
DATA: {item.get("received_at", "desconhecida")}

PROCESSO:
1. Identifica as afirmacoes principais
2. Faz {n_searches} web_search procurando fontes INDEPENDENTES
3. Conta quantas fontes independentes confirmam (precisa de 3+ para aprovacao)
4. Devolve JSON final"""

    response = chat_with_tools(
        model=MODEL,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    return _parse_fc_response(response)


def _check_item_editorial(item: dict) -> dict:
    """V3 EDITORIAL: Verify facts for Wilson's manual injections. Respects editorial priority."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system = f"""Es um fact-checker do NoticIA. O editor-chefe humano (Wilson) submeteu esta noticia manualmente.
Hoje e {hoje}.

REGRAS:
1. RESPEITA a prioridade editorial — Wilson considera esta noticia relevante.
2. Verifica os FACTOS, nao a relevancia (essa ja foi decidida por Wilson).
3. Se os factos sao verificaveis → aprova com certainty adequada.
4. Se nao verificaveis → marca needs_review (NAO rejeita automaticamente).
5. Procura fontes primarias para corroborar.

SCORING GRANULAR (NUNCA multiplos de 0.05):
certainty_score: confianca nos factos (threshold normal)
bias_score: vies do conteudo original

DEVOLVE JSON:
{{
  "aprovado": true/false,
  "certainty_score": 0.XX,
  "bias_score": 0.XX,
  "veracidade": "confirmado|parcial|nao_verificavel",
  "fontes_encontradas": ["url1", "url2"],
  "data_real_evento": "2026-03-XX",
  "publish_recommendation": "editorial|fact_check|needs_review",
  "notas": "..."
}}"""

    user = f"""VERIFICA esta noticia submetida pelo editor-chefe:

TITULO: {item.get("title", "")}
CONTEUDO: {item.get("content", "")[:1200]}
FONTE: {item.get("url", "")}
AREA: {item.get("area", "")}

Faz 1-2 web_search para confirmar os factos. Devolve JSON final."""

    response = chat_with_tools(
        model=MODEL,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    return _parse_fc_response(response)


def _parse_fc_response(response: str) -> dict:
    """Parse JSON from FC response, handling various formats."""
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

    return {"aprovado": False, "certainty_score": 0.0, "notas": "Falha a parsear resposta FC"}


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

    # V3: save bias_verdict and media_audit for the editorial decisor
    bias_verdict_data = {
        "bias_type": verdict.get("bias_type", "none"),
        "omitted_facts": verdict.get("omitted_facts", []),
        "counter_narrative": verdict.get("counter_narrative", ""),
    }
    media_audit_data = {
        "publish_recommendation": verdict.get("publish_recommendation", "discard"),
        "factos_correctos": verdict.get("factos_correctos", True),
    }

    update: dict = {
        "status": "approved" if aprovado else "fact_check",
        "fact_check_summary": fact_check_summary,
        "bias_score": bias,
        "bias_analysis": bias_analysis,
        "bias_verdict": bias_verdict_data,
        "media_audit": media_audit_data,
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
