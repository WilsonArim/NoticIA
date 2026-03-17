"""
Agente Escritor — Qwen 3.5 122B (tool calling, PT-PT nativo)
Escreve artigos jornalísticos em PT-PT a partir de items 'approved'.
"""
import os
import json
import logging
import re

from supabase import create_client

from openclaw.agents.ollama_client import chat

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_ESCRITOR", "qwen3.5:122b")
BATCH_SIZE = int(os.getenv("ESCRITOR_BATCH_SIZE", "5"))


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
            artigo = _escrever_artigo(item)
            _publicar_artigo(supabase, item, artigo)
        except Exception as e:
            logger.error("Escritor erro item %s: %s", item["id"], e)


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

    supabase.table("articles").insert({
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
        "status": "processed",
        "tags": artigo.get("tags", []),
        "language": "pt",
    }).execute()

    supabase.table("intake_queue").update({
        "status": "processed",
    }).eq("id", item["id"]).execute()

    logger.info("Escritor: artigo criado '%s'", artigo.get("titulo", "")[:50])


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
