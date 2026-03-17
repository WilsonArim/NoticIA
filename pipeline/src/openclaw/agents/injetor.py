"""
Agente Injetor — Pipeline express para notícias manuais.

Recebe URL + metadados via CLI, executa triagem → fact-check → escrita
de forma síncrona e imediata, sem esperar pelos ciclos do scheduler.

USO:
    cd pipeline
    python -m openclaw.agents.injetor --url "https://..." [opções]

OPÇÕES:
    --url         URL da notícia fonte (obrigatório)
    --titulo      Título da notícia (opcional — gerado automaticamente se vazio)
    --resumo      Resumo/conteúdo (opcional — o fact-checker enriquece com pesquisa)
    --area        Área editorial (default: mundo)
    --prioridade  p1 / p2 / p3 (default: p1 — máxima)

EXEMPLOS:
    # Notícia com título e resumo
    python -m openclaw.agents.injetor \\
        --url "https://fatf-gafi.org/..." \\
        --titulo "FATF mantém Irão em lista negra" \\
        --resumo "O FATF confirmou hoje a manutenção do Irão na lista negra..." \\
        --area geopolitica

    # Notícia só com URL — fact-checker pesquisa e enriquece
    python -m openclaw.agents.injetor \\
        --url "https://amnesty.org/..." \\
        --area justica --prioridade p2
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

# Carrega pipeline/.env antes de qualquer import que use env vars
load_dotenv()

from supabase import create_client  # noqa: E402

from openclaw.agents.triagem import _classify_item  # noqa: E402
from openclaw.agents.fact_checker import _check_item, _apply_verdict  # noqa: E402
from openclaw.agents.escritor import _escrever_artigo, _publicar_artigo  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [injetor] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("injetor")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

AREAS_VALIDAS = [
    "portugal", "europa", "mundo", "economia", "tecnologia",
    "ciencia", "saude", "cultura", "desporto", "geopolitica",
    "defesa", "clima", "sociedade", "justica", "educacao",
]


# ── Ponto de entrada público ────────────────────────────────────────────


def run_injetor(url: str, titulo: str = "", resumo: str = "", area: str = "mundo", prioridade: str = "p1"):
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # 1. Verificar duplicado por URL
    existing = (
        supabase.table("intake_queue")
        .select("id, status, title")
        .eq("url", url)
        .limit(1)
        .execute()
    )

    if existing.data:
        dup = existing.data[0]
        logger.warning(
            "URL já existe na fila: id=%s, status=%s, título='%s'",
            dup["id"], dup["status"], dup.get("title", "")[:60],
        )
        logger.info("A continuar pipeline a partir do estado actual...")
        item = supabase.table("intake_queue").select("*").eq("id", dup["id"]).single().execute().data
        _executar_pipeline(supabase, item)
        return

    # 2. Inserir nova notícia na fila
    titulo_final = titulo or url
    logger.info("Injetor: inserindo '%s'", titulo_final[:70])

    result = supabase.table("intake_queue").insert({
        "title": titulo_final,
        "content": resumo,
        "url": url,
        "area": area,
        "score": 0.95,        # injecção manual = prioridade máxima no batch
        "status": "pending",
        "priority": prioridade,
        "language": "pt",
        "metadata": {
            "source_agent": "manual",
            "injetado_em": datetime.now(timezone.utc).isoformat(),
        },
    }).execute()

    item = result.data[0]
    logger.info("Inserido com id=%s. A iniciar pipeline...", item["id"])
    _executar_pipeline(supabase, item)


# ── Pipeline síncrono ───────────────────────────────────────────────────


def _executar_pipeline(supabase, item: dict):
    item_id = item["id"]
    status = item.get("status", "pending")

    # ── FASE 1: Triagem ──────────────────────────────────────────────────
    if status == "pending":
        logger.info("")
        logger.info("══ FASE 1 — Triagem (DeepSeek V3.2) ══════════════════════════")

        triagem_result = _classify_item(item)

        if triagem_result.get("rejeitar"):
            motivo = triagem_result.get("notas", "Rejeitado pela triagem")
            supabase.table("intake_queue").update({
                "status": "auditor_failed",
                "error_message": motivo,
            }).eq("id", item_id).execute()
            logger.warning("Triagem REJEITOU: %s", motivo)
            logger.info("Pipeline terminado — artigo rejeitado na triagem.")
            return

        nova_area = triagem_result.get("area", item.get("area", "mundo"))
        novo_score = triagem_result.get("score", item.get("score", 0.5))

        supabase.table("intake_queue").update({
            "status": "auditor_approved",
            "area": nova_area,
            "score": novo_score,
            "metadata": {
                **(item.get("metadata") or {}),
                "triagem_notes": triagem_result.get("notas", ""),
            },
        }).eq("id", item_id).execute()

        logger.info(
            "Triagem APROVADA ✓  área=%s | score=%.2f | nota: %s",
            nova_area, novo_score, triagem_result.get("notas", "")[:80],
        )

        # Re-fetch com dados actualizados
        item = supabase.table("intake_queue").select("*").eq("id", item_id).single().execute().data
        status = "auditor_approved"

    # ── FASE 2: Fact-checking ───────────────────────────────────────────
    if status == "auditor_approved":
        logger.info("")
        logger.info("══ FASE 2 — Fact-Check (Nemotron 3 Super) ════════════════════")

        verdict = _check_item(item)
        _apply_verdict(supabase, item, verdict)

        certainty = float(verdict.get("certainty_score", 0.0))
        bias = float(verdict.get("bias_score", 0.5))
        aprovado = verdict.get("aprovado", False) and certainty >= 0.70

        if not aprovado:
            logger.warning(
                "Fact-check REJEITOU (certainty=%.2f, bias=%.2f): %s",
                certainty, bias, verdict.get("notas", "")[:100],
            )
            logger.info("Pipeline terminado — artigo rejeitado no fact-check.")
            return

        logger.info(
            "Fact-check APROVADO ✓  certainty=%.2f | bias=%.2f | fontes=%d",
            certainty, bias,
            len(verdict.get("fontes_encontradas", [])),
        )
        logger.info("  Notas: %s", verdict.get("notas", "")[:120])

        # Re-fetch com fact_check_summary preenchido
        item = supabase.table("intake_queue").select("*").eq("id", item_id).single().execute().data
        status = "approved"

    # ── FASE 3: Escrita ─────────────────────────────────────────────────
    if status == "approved":
        logger.info("")
        logger.info("══ FASE 3 — Escritor (Nemotron 3 Super) ═══════════════════════")

        artigo = _escrever_artigo(item)
        _publicar_artigo(supabase, item, artigo)

        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info("║  ✅ ARTIGO PUBLICADO COM SUCESSO                             ║")
        logger.info("╠══════════════════════════════════════════════════════════════╣")
        logger.info("║  Título : %s", (artigo.get("titulo", "")[:54]).ljust(54) + "  ║")
        logger.info("║  Área   : %-54s  ║", item.get("area", ""))
        logger.info("║  Slug   : %-54s  ║", artigo.get("slug", "")[:54])
        logger.info("╚══════════════════════════════════════════════════════════════╝")
        return

    logger.warning("Item em status inesperado '%s' — pipeline não executou.", status)


# ── CLI ─────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NoticIA — Injectar notícia manual no pipeline (triagem → fact-check → escrita)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Exemplos:
  python -m openclaw.agents.injetor --url "https://fatf-gafi.org/..." --area geopolitica
  python -m openclaw.agents.injetor --url "https://..." --titulo "..." --resumo "..." --area economia --prioridade p2
        """,
    )
    parser.add_argument("--url", required=True, help="URL da notícia fonte (obrigatório)")
    parser.add_argument("--titulo", default="", help="Título da notícia (opcional)")
    parser.add_argument("--resumo", default="", help="Resumo / conteúdo da notícia (opcional)")
    parser.add_argument(
        "--area",
        default="mundo",
        choices=AREAS_VALIDAS,
        help="Área editorial (default: mundo)",
    )
    parser.add_argument(
        "--prioridade",
        default="p1",
        choices=["p1", "p2", "p3"],
        help="Prioridade da notícia (default: p1)",
    )

    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error(
            "SUPABASE_URL e SUPABASE_SERVICE_KEY precisam de estar configurados em pipeline/.env"
        )
        sys.exit(1)

    run_injetor(
        url=args.url,
        titulo=args.titulo,
        resumo=args.resumo,
        area=args.area,
        prioridade=args.prioridade,
    )
