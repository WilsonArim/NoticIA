"""
Agente Escritor — Nemotron 3 Super (PT-PT nativo)
Escreve artigos jornalísticos em PT-PT a partir de items 'approved'.
Publica directamente com status='published' (sem etapa intermédia 'processed').
"""
import os
import json
import logging
import re
from datetime import datetime, timezone, timedelta

from supabase import create_client

from openclaw.agents.ollama_client import chat

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_ESCRITOR", "nemotron-3-super:cloud")
BATCH_SIZE = int(os.getenv("ESCRITOR_BATCH_SIZE", "15"))
MAX_EVENT_AGE_DAYS = int(os.getenv("MAX_EVENT_AGE_DAYS", "7"))
CERTAINTY_THRESHOLD = float(os.getenv("ESCRITOR_CERTAINTY_THRESHOLD", "0.895"))


def run_escritor():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # --- pipeline_runs logging: início ---
    run_id = None
    try:
        run_row = supabase.table("pipeline_runs").insert({
            "stage": "escritor",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events_in": 0,
            "events_out": 0,
        }).execute()
        run_id = run_row.data[0]["id"] if run_row.data else None
    except Exception as e:
        logger.warning("Escritor: falha ao criar pipeline_run: %s", e)

    # V3: reads 'ready_to_write' (post-decisor) AND 'approved' (backward compat)
    result = (
        supabase.table("intake_queue")
        .select("*")
        .in_("status", ["ready_to_write", "approved"])
        .order("score", desc=True)
        .limit(BATCH_SIZE)
        .execute()
    )

    items = result.data or []
    if not items:
        logger.info("Escritor: sem items aprovados")
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

    logger.info("Escritor: escrevendo %d artigos com %s", len(items), MODEL)
    published_count = 0

    for item in items:
        try:
            # ── Guard final de frescura — última linha de defesa ──────────
            fact_summary = item.get("fact_check_summary") or {}
            data_real = fact_summary.get("data_real_evento") or (item.get("metadata") or {}).get("data_real_evento")
            if _event_is_stale(data_real):
                supabase.table("intake_queue").update({
                    "status": "fact_check",
                    "error_message": f"ESCRITOR_STALE: evento de {data_real} (>{MAX_EVENT_AGE_DAYS} dias)",
                }).eq("id", item["id"]).execute()
                logger.warning("Escritor: STALE bloqueado antes de publicar — '%s' (%s)", item.get("title", "")[:60], data_real)
                continue

            artigo = _escrever_artigo(item)
            _publicar_artigo(supabase, item, artigo)
            published_count += 1
        except Exception as e:
            err_str = str(e)
            if "QUALITY_GATE" in err_str:
                # Certainty abaixo do threshold — marcar como fact_check para não reprocessar
                supabase.table("intake_queue").update({
                    "status": "fact_check",
                    "error_message": err_str[:400],
                }).eq("id", item["id"]).execute()
                logger.warning("Escritor quality gate rejeitou '%s': %s", item.get("title", "")[:50], err_str[:100])
            else:
                logger.error("Escritor erro item %s: %s", item["id"], e)

    # --- pipeline_runs logging: fim ---
    if run_id:
        try:
            supabase.table("pipeline_runs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": len(items),
                "events_out": published_count,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Escritor: falha ao actualizar pipeline_run: %s", e)


def _event_is_stale(data_real_str: str | None) -> bool:
    """Retorna True se a data real do evento for mais antiga que MAX_EVENT_AGE_DAYS."""
    if not data_real_str or len(str(data_real_str)) < 10:
        return False
    try:
        evento_date = datetime.strptime(str(data_real_str)[:10], "%Y-%m-%d").date()
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=MAX_EVENT_AGE_DAYS)
        return evento_date < cutoff
    except ValueError:
        return False


def _escrever_artigo(item: dict) -> dict:
    """V3: Write article using template based on article_type."""
    metadata = item.get("metadata") or {}
    article_type = metadata.get("article_type", "standard")
    is_dossie = metadata.get("source_agent") == "dossie"

    fact_summary = item.get("fact_check_summary") or {}
    bias_verdict = item.get("bias_verdict") or {}
    notas_fc = fact_summary.get("notas", "")

    # Route to the appropriate template
    if article_type == "expose":
        prompt = _template_expose(item, fact_summary, bias_verdict)
    elif article_type == "omission":
        prompt = _template_omission(item, fact_summary, bias_verdict)
    elif article_type == "alt_news":
        prompt = _template_alt_news(item, fact_summary)
    elif article_type == "fact_check":
        prompt = _template_fact_check(item, fact_summary, bias_verdict)
    elif article_type == "editorial":
        prompt = _template_editorial(item, fact_summary)
    else:
        prompt = _template_standard(item, fact_summary)

    response = chat(MODEL, [{"role": "user", "content": prompt}], temperature=0.4, max_tokens=3000)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        raw_json = response[start:end]
        result = json.loads(raw_json, strict=False)
        # Inject article_type into result for the publisher
        result["_article_type"] = article_type
        return result

    raise ValueError(f"Escritor: resposta invalida: {response[:200]}")


def _base_rules_ptpt() -> str:
    """Common PT-PT writing rules for all templates."""
    return """REGRAS LINGUISTICAS PT-PT:
- "facto" (nao "fato"), "equipa" (nao "time"), "rede" (nao "internet"), "telemovel" (nao "celular")
- Tom serio, directo, sem sensacionalismo
- Factos primeiro, contexto depois

REGRAS DO TITULO:
- O titulo DEVE ser factualmente correcto e coerente com o corpo
- Se o titulo sugerido e ambiguo, REESCREVE-O
- O sujeito do titulo deve ser o protagonista principal (quem fez a accao)"""


def _json_format() -> str:
    """Common JSON output format."""
    return """Escreve em JSON:
{
  "titulo": "Titulo factual e directo (max 90 chars)",
  "subtitulo": "Subtitulo com contexto (max 140 chars)",
  "lead": "Paragrafo abertura (2-3 frases: quem, o que, quando, onde)",
  "corpo_html": "<p>Corpo completo em HTML...</p>",
  "tags": ["tag1", "tag2", "tag3"],
  "slug": "titulo-em-kebab-case-sem-acentos"
}"""


def _template_expose(item: dict, fc: dict, bv: dict) -> str:
    """EXPOSE template — unmask media bias."""
    bias_type = bv.get("bias_type", "desconhecido")
    omitted = bv.get("omitted_facts", [])
    counter = bv.get("counter_narrative", "")
    fontes = fc.get("fontes_encontradas", [])

    return f"""Es um jornalista investigativo do NoticIA. A tua missao e DESMASCARAR o vies dos media.

{_base_rules_ptpt()}

DADOS DO EXPOSE:
Titulo original (media): {item.get("title", "")}
Conteudo original: {item.get("content", "")[:800]}
Fonte media: {item.get("url", "")}
Tipo de vies detectado: {bias_type}
Factos omitidos pelo media: {', '.join(omitted) if omitted else 'nenhum identificado'}
Contra-narrativa: {counter or 'nao disponivel'}
Fontes primarias: {', '.join(fontes[:4]) if fontes else 'nenhuma'}
Notas do fact-checker: {fc.get("notas", "")}

ESTRUTURA DO EXPOSE:
1. O que os media disseram (resumo factual da noticia original)
2. O que os media omitiram (factos que faltam, com fontes)
3. O outro lado da historia (contra-narrativa com evidencia)
4. Fontes primarias (links para dados oficiais/originais)

Tom: Factual, directo, sem sensacionalismo. Deixa os factos falar.
NAO uses linguagem inflamatoria. Mostra o vies com FACTOS, nao com opiniao.

{_json_format()}"""


def _template_omission(item: dict, fc: dict, bv: dict) -> str:
    """OMISSION template — cover what media ignores."""
    omitted = bv.get("omitted_facts", [])
    fontes = fc.get("fontes_encontradas", [])

    return f"""Es um jornalista do NoticIA. Estas a cobrir algo que os media portugueses IGNORAM ou SUB-REPORTAM.

{_base_rules_ptpt()}

DADOS:
Evento: {item.get("title", "")}
Conteudo: {item.get("content", "")[:800]}
Fonte: {item.get("url", "")}
Area: {item.get("area", "mundo")}
Factos omitidos pelos media: {', '.join(omitted) if omitted else 'contexto geral omitido'}
Fontes primarias: {', '.join(fontes[:4]) if fontes else 'nenhuma'}
Notas do fact-checker: {fc.get("notas", "")}

ESTRUTURA:
1. O que aconteceu (factos verificados)
2. Porque e importante (impacto, contexto)
3. O que os media nao cobrem e porque (analise, se aplicavel)
4. Fontes (links)

Inclui no subtitulo ou lead: "Os media portugueses nao cobriram esta noticia" (se aplicavel).

{_json_format()}"""


def _template_alt_news(item: dict, fc: dict) -> str:
    """ALT-NEWS template — verified alternative source news."""
    fontes = fc.get("fontes_encontradas", [])

    return f"""Es um jornalista rigoroso. Escreve um artigo em PT-PT sobre uma noticia verificada que NAO foi coberta pela imprensa mainstream.

{_base_rules_ptpt()}

DADOS:
Titulo: {item.get("title", "")}
Conteudo: {item.get("content", "")[:800]}
Fonte original: {item.get("url", "")}
Area: {item.get("area", "mundo")}
Certainty: {fc.get("certainty_score", 0.8)}
Fontes de verificacao: {', '.join(fontes[:4]) if fontes else 'nenhuma'}
Notas do fact-checker: {fc.get("notas", "")}

ESTRUTURA:
1. O que aconteceu (factos verificados por 3+ fontes)
2. Contexto e impacto
3. Fontes de verificacao
4. Nota: "Esta noticia nao foi coberta pela imprensa portuguesa mainstream."

Tom: Factual, credivel, jornalismo puro.

{_json_format()}"""


def _template_fact_check(item: dict, fc: dict, bv: dict) -> str:
    """FACT-CHECK template — point-by-point verification."""
    fontes = fc.get("fontes_encontradas", [])
    counter = bv.get("counter_narrative", "")

    return f"""Es um fact-checker jornalistico. Escreve uma desmontagem ponto a ponto em PT-PT.

{_base_rules_ptpt()}

DADOS:
Afirmacao/Noticia: {item.get("title", "")}
Conteudo: {item.get("content", "")[:800]}
Fonte: {item.get("url", "")}
Fontes de verificacao: {', '.join(fontes[:4]) if fontes else 'nenhuma'}
Contra-narrativa: {counter or 'n/a'}
Notas do FC: {fc.get("notas", "")}

ESTRUTURA (formato fact-check):
Para cada afirmacao principal:
  - AFIRMACAO: "X disse que Y"
  - VERIFICACAO: O que as fontes primarias dizem
  - VEREDICTO: Verdadeiro / Parcialmente verdadeiro / Falso / Enganador (com provas)

Conclusao final com veredicto geral.

{_json_format()}"""


def _template_editorial(item: dict, fc: dict) -> str:
    """EDITORIAL template — Wilson's manual injection."""
    fontes = fc.get("fontes_encontradas", [])

    return f"""Es um jornalista rigoroso. O editor-chefe submeteu esta noticia para publicacao. Escreve em PT-PT.

{_base_rules_ptpt()}

DADOS:
Titulo: {item.get("title", "")}
Conteudo: {item.get("content", "")[:1000]}
Fonte: {item.get("url", "")}
Area: {item.get("area", "mundo")}
Fontes de verificacao: {', '.join(fontes[:4]) if fontes else 'nenhuma'}
Notas do FC: {fc.get("notas", "")}

Escreve o artigo completo. Tom serio e profissional.

{_json_format()}"""


def _template_standard(item: dict, fc: dict) -> str:
    """STANDARD template — backward compatible, same as original escritor."""
    notas_fc = fc.get("notas", "")

    hoje = datetime.now(timezone.utc)
    hoje_str = hoje.strftime("%Y-%m-%d")
    DIAS_SEMANA_PT = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
                      "sexta-feira", "sabado", "domingo"]
    dia_semana_hoje = DIAS_SEMANA_PT[hoje.weekday()]
    data_real = fc.get("data_real_evento") or ""
    dia_semana_evento = ""
    if data_real and len(str(data_real)) >= 10:
        try:
            evento_dt = datetime.strptime(str(data_real)[:10], "%Y-%m-%d")
            dia_semana_evento = DIAS_SEMANA_PT[evento_dt.weekday()]
        except ValueError:
            pass
    if data_real and dia_semana_evento:
        ctx_temporal = f"- Data real do evento: {data_real} ({dia_semana_evento})"
    else:
        ctx_temporal = "- Data real do evento: desconhecida — usa termos vagos como «recentemente»"

    return f"""Es um jornalista rigoroso. Escreve um artigo em **PT-PT** (Portugal, nao Brasil).

CONTEXTO TEMPORAL (OBRIGATORIO — usa estas datas, NAO inventes):
- Hoje: {hoje_str} ({dia_semana_hoje})
{ctx_temporal}
- NUNCA inventes o dia da semana — calcula a partir das datas acima

{_base_rules_ptpt()}

DADOS DO ARTIGO:
Titulo sugerido: {item.get("title", "")}
Conteudo base: {item.get("content", "")[:1000]}
Fonte: {item.get("url", "")}
Area: {item.get("area", "mundo")}
Notas do fact-checker: {notas_fc}
Certainty: {fc.get("certainty_score", 0.8)}

{_json_format()}"""



def _publicar_artigo(supabase, item: dict, artigo: dict):
    """Publica artigo + fontes + claims numa transação atómica via stored procedure.

    Usa supabase.rpc('publish_article_with_sources', payload) que insere tudo
    no Postgres numa única transação — ou tudo ou nada. Resolve definitivamente
    o problema de artigos publicados sem fontes.
    """
    slug = artigo.get("slug", "") or _slugify(artigo.get("titulo", item.get("title", "")))

    fact_summary = item.get("fact_check_summary") or {}
    certainty = float(fact_summary.get("certainty_score", 0.0))

    # CRIT-005: Quality gate — rejeita artigos abaixo do threshold de certeza
    if certainty < CERTAINTY_THRESHOLD:
        raise ValueError(
            f"QUALITY_GATE: certainty_score={certainty:.2f} < threshold={CERTAINTY_THRESHOLD} "
            f"para '{item.get('title', '')[:60]}'"
        )

    # Juntar fontes: URL original + fontes do fact-checker (dedup, máx 6)
    fontes_fc = fact_summary.get("fontes_encontradas", [])
    url_original = item.get("url", "")
    todas_fontes: list[str] = []
    vistas: set[str] = set()
    for url in ([url_original] + list(fontes_fc)):
        if url and url.startswith("http") and url not in vistas:
            todas_fontes.append(url)
            vistas.add(url)
        if len(todas_fontes) >= 6:
            break

    # Notas do fact-checker para o claim
    notas = fact_summary.get("notas", "")
    claim_text = (artigo.get("lead") or notas or item.get("title", "Factos verificados"))[:500]

    # Payload para a stored procedure atómica
    payload = {
        "title": artigo.get("titulo", item.get("title", "")),
        "subtitle": artigo.get("subtitulo", ""),
        "slug": slug,
        "lead": artigo.get("lead", ""),
        "body": artigo.get("corpo_html", ""),
        "body_html": artigo.get("corpo_html", ""),
        "area": item.get("area", "mundo"),
        "priority": item.get("priority", "p2"),
        "certainty_score": certainty,
        "bias_score": float(item.get("bias_score", 0.20)),
        "tags": artigo.get("tags", []),
        "fontes": todas_fontes,
        "claim_text": claim_text,
        "claim_subject": item.get("title", "")[:100],
        "intake_queue_id": item["id"],
        "article_type": artigo.get("_article_type", (item.get("metadata") or {}).get("article_type", "standard")),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.rpc("publish_article_with_sources", {"payload": payload}).execute()

    if result.data and result.data.get("success"):
        logger.info(
            "Escritor: artigo publicado '%s' (id=%s, fontes=%d)",
            artigo.get("titulo", "")[:50],
            result.data.get("article_id", "?"),
            result.data.get("sources_count", 0),
        )
    else:
        logger.error("Escritor: RPC falhou para '%s': %s", artigo.get("titulo", "")[:50], result.data)


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[àáâãä]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[ñ]", "n", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip())
    return text[:80]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_escritor()
