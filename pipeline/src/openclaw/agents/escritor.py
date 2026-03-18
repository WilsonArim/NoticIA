"""
Agente Escritor — Nemotron 3 Super (PT-PT nativo)
Escreve artigos jornalísticos em PT-PT a partir de items 'approved'.
Publica directamente com status='published' (sem etapa intermédia 'processed').
"""
import os
import json
import logging
import re
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from supabase import create_client

from openclaw.agents.ollama_client import chat

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_ESCRITOR", "nemotron-3-super:cloud")
BATCH_SIZE = int(os.getenv("ESCRITOR_BATCH_SIZE", "5"))
MAX_EVENT_AGE_DAYS = int(os.getenv("MAX_EVENT_AGE_DAYS", "7"))


def run_escritor():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("intake_queue")
        .select("*")
        .eq("status", "approved")
        .order("score", desc=True)
        .limit(BATCH_SIZE)
        .execute()
    )

    items = result.data or []
    if not items:
        logger.info("Escritor: sem items aprovados")
        return

    logger.info("Escritor: escrevendo %d artigos com %s", len(items), MODEL)

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
    metadata = item.get("metadata") or {}
    is_dossie = metadata.get("source_agent") == "dossie"

    fact_summary = item.get("fact_check_summary") or {}
    notas_fc = fact_summary.get("notas", "")

    prompt = f"""És um jornalista rigoroso. Escreve um artigo em **PT-PT** (Portugal, não Brasil).

REGRAS LINGUÍSTICAS PT-PT:
- "facto" (não "fato"), "equipa" (não "time"), "rede" (não "internet"), "telemóvel" (não "celular")
- Tom sério, directo, sem sensacionalismo
- Factos primeiro, contexto depois
{"- Este artigo vem do dossiê de investigação: apresenta os factos tal como são, sem suavizar a realidade" if is_dossie else ""}

DADOS DO ARTIGO:
Título sugerido: {item.get("title", "")}
Conteúdo base: {item.get("content", "")[:1000]}
Fonte: {item.get("url", "")}
Área: {item.get("area", "mundo")}
Notas do fact-checker: {notas_fc}
Certainty: {fact_summary.get("certainty_score", 0.8)}

Escreve o artigo completo em JSON:
{{
  "titulo": "Título factual e directo (máx 90 chars)",
  "subtitulo": "Subtítulo que acrescenta contexto (máx 140 chars)",
  "lead": "Parágrafo de abertura (2-3 frases, responde: quem, o quê, quando, onde)",
  "corpo_html": "<p>Corpo completo em HTML...</p>",
  "tags": ["tag1", "tag2", "tag3"],
  "slug": "titulo-em-kebab-case-sem-acentos"
}}"""

    response = chat(MODEL, [{"role": "user", "content": prompt}], temperature=0.4, max_tokens=3000)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    raise ValueError(f"Escritor: resposta inválida: {response[:200]}")


def _publicar_artigo(supabase, item: dict, artigo: dict):
    slug = artigo.get("slug", "") or _slugify(artigo.get("titulo", item.get("title", "")))

    fact_summary = item.get("fact_check_summary") or {}
    certainty = fact_summary.get("certainty_score", 0.8)

    result = supabase.table("articles").insert({
        "title": artigo.get("titulo", item.get("title", "")),
        "subtitle": artigo.get("subtitulo", ""),
        "slug": slug,
        "lead": artigo.get("lead", ""),
        "body": artigo.get("corpo_html", ""),
        "body_html": artigo.get("corpo_html", ""),
        "area": item.get("area", "mundo"),
        "priority": item.get("priority", "p2"),
        "certainty_score": certainty,
        "bias_score": item.get("bias_score", 0.20),
        "status": "published",  # publica directamente — sem etapa 'processed' (constraint)
        "tags": artigo.get("tags", []),
        "language": "pt",
        "verification_status": "none",
    }).select("id").single().execute()

    article_id = result.data.get("id") if result.data else None

    # Inserir fontes, claim e ligações para que apareçam no frontend
    if article_id:
        _inserir_fontes_do_artigo(supabase, article_id, item, artigo)

    supabase.table("intake_queue").update({
        "status": "processed",
    }).eq("id", item["id"]).execute()

    logger.info("Escritor: artigo publicado '%s'", artigo.get("titulo", "")[:50])


def _inserir_fontes_do_artigo(supabase, article_id: str, item: dict, artigo: dict):
    """Insere sources + claim principal + article_claims + claim_sources.

    Usa as fontes descobertas pelo fact-checker (fact_check_summary.fontes_encontradas)
    mais a URL original da notícia. Sem estas inserções as fontes não aparecem no frontend.
    """
    fact_summary = item.get("fact_check_summary") or {}
    fontes_fc = fact_summary.get("fontes_encontradas", [])

    # Juntar URL original + fontes do fact-checker (dedup, máx 6)
    url_original = item.get("url", "")
    todas_fontes: list[str] = []
    vistas: set[str] = set()
    for url in ([url_original] + list(fontes_fc)):
        if url and url.startswith("http") and url not in vistas:
            todas_fontes.append(url)
            vistas.add(url)
        if len(todas_fontes) >= 6:
            break

    if not todas_fontes:
        logger.debug("Escritor: sem fontes para artigo %s", article_id)
        return

    # 1. Inserir / reutilizar sources
    source_ids: list[str] = []
    for url in todas_fontes:
        try:
            domain = urlparse(url).netloc or url[:50]
            content_hash = hashlib.md5(url.encode()).hexdigest()

            existing = (
                supabase.table("sources")
                .select("id")
                .eq("content_hash", content_hash)
                .maybeSingle()
                .execute()
            )
            if existing.data:
                source_ids.append(existing.data["id"])
                continue

            ins = (
                supabase.table("sources")
                .insert({
                    "url": url,
                    "domain": domain,
                    "title": domain,
                    "content_hash": content_hash,
                    "source_type": "web",
                    "reliability_score": 0.75,
                    "metadata": {"via": "fact_checker"},
                })
                .select("id")
                .single()
                .execute()
            )
            if ins.data:
                source_ids.append(ins.data["id"])
        except Exception as e:
            logger.warning("Escritor: erro ao inserir source %s: %s", url[:60], e)

    if not source_ids:
        return

    # 2. Criar claim principal com o lead do artigo (ou as notas do fact-checker)
    notas = fact_summary.get("notas", "")
    claim_text = (artigo.get("lead") or notas or item.get("title", "Factos verificados"))[:500]
    claim_id: str | None = None
    try:
        c = (
            supabase.table("claims")
            .insert({
                "original_text": claim_text,
                "subject": item.get("title", "")[:100],
                "predicate": "verificado por",
                "object": "múltiplas fontes",
                "verification_status": "verified",
                "confidence_score": min(1.0, float(fact_summary.get("certainty_score", 0.8))),
            })
            .select("id")
            .single()
            .execute()
        )
        claim_id = c.data.get("id") if c.data else None
    except Exception as e:
        logger.warning("Escritor: erro ao inserir claim: %s", e)

    if not claim_id:
        return

    # 3. Ligar claim ao artigo
    try:
        supabase.table("article_claims").insert({
            "article_id": article_id,
            "claim_id": claim_id,
            "position": 0,
        }).execute()
    except Exception as e:
        logger.warning("Escritor: erro ao inserir article_claims: %s", e)

    # 4. Ligar cada source ao claim
    for source_id in source_ids:
        try:
            supabase.table("claim_sources").insert({
                "claim_id": claim_id,
                "source_id": source_id,
                "supports": True,
                "excerpt": None,
            }).execute()
        except Exception as e:
            logger.warning("Escritor: erro ao inserir claim_sources (source=%s): %s", source_id, e)


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
