"""
Decisor Editorial V3 — Gate entre o Fact-Checker e o Escritor.

Decide o que publicar e como, baseado nos resultados do FC e na vertente.
Regra central: noticias dos media sem vies = DESCARTA (nao nos interessa).

Status flow:
  approved (FC) → [Decisor] → ready_to_write (com article_type)
                            → discarded (noticia correcta sem vies)
                            → wilson_review (ambiguo, enviado ao Wilson)

Frequencia: cada 10 min via scheduler_ollama.py
Nao usa LLM — decisao deterministica baseada nos campos do FC.
"""
import logging
import os
from datetime import datetime, timezone

from supabase import create_client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BATCH_SIZE = int(os.getenv("DECISOR_BATCH_SIZE", "20"))

# Thresholds for media audit decisions
BIAS_EXPOSE_THRESHOLD = float(os.getenv("BIAS_EXPOSE_THRESHOLD", "0.20"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WILSON_CHAT_ID = os.getenv("WILSON_CHAT_ID", "")


def run_editorial_decisor() -> dict:
    """Process approved items and route them based on vertente and FC results.

    Returns stats dict with counts per decision.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Decisor: SUPABASE_URL ou SERVICE_KEY em falta")
        return {}

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # --- pipeline_runs logging ---
    run_id = None
    try:
        run_row = supabase.table("pipeline_runs").insert({
            "stage": "editorial_decisor",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events_in": 0,
            "events_out": 0,
        }).execute()
        run_id = run_row.data[0]["id"] if run_row.data else None
    except Exception as e:
        logger.warning("Decisor: falha ao criar pipeline_run: %s", e)

    # ── Auto-expire: wilson_review items older than 2 days → discarded ──
    REVIEW_EXPIRE_DAYS = int(os.getenv("REVIEW_EXPIRE_DAYS", "2"))
    try:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=REVIEW_EXPIRE_DAYS)).isoformat()
        expired = (
            supabase.table("intake_queue")
            .select("id, title")
            .eq("status", "wilson_review")
            .lt("created_at", cutoff)
            .execute()
        )
        if expired.data:
            for ex in expired.data:
                supabase.table("intake_queue").update({
                    "status": "discarded",
                    "error_message": f"AUTO_EXPIRE: wilson_review sem decisao ha >{REVIEW_EXPIRE_DAYS} dias",
                }).eq("id", ex["id"]).execute()
            logger.info("Decisor: %d wilson_review expirados (>%dd) → discarded", len(expired.data), REVIEW_EXPIRE_DAYS)
    except Exception as e:
        logger.warning("Decisor: falha ao expirar wilson_review antigos: %s", e)

    # Fetch items that passed FC (status='approved')
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
        logger.info("Decisor: sem items aprovados para processar")
        _finalize_run(supabase, run_id, {"total": 0})
        return {"total": 0}

    stats = {
        "total": len(items),
        "ready_to_write": 0,
        "discarded": 0,
        "wilson_review": 0,
        "errors": 0,
        "by_type": {},
    }

    logger.info("Decisor: processando %d items aprovados pelo FC", len(items))

    for item in items:
        try:
            decision = _decide(item)
            _apply_decision(supabase, item, decision)

            if decision["status"] == "ready_to_write":
                stats["ready_to_write"] += 1
                at = decision.get("article_type", "standard")
                stats["by_type"][at] = stats["by_type"].get(at, 0) + 1
            elif decision["status"] == "discarded":
                stats["discarded"] += 1
            elif decision["status"] == "wilson_review":
                stats["wilson_review"] += 1

        except Exception as e:
            logger.error("Decisor erro item %s: %s", item.get("id", "?"), e)
            stats["errors"] += 1

    logger.info(
        "Decisor concluido: total=%d | ready_to_write=%d (tipos: %s) | "
        "discarded=%d | wilson_review=%d | errors=%d",
        stats["total"], stats["ready_to_write"], stats["by_type"],
        stats["discarded"], stats["wilson_review"], stats["errors"],
    )

    _finalize_run(supabase, run_id, stats)
    return stats


def _decide(item: dict) -> dict:
    """Deterministic + heuristic decision based on vertente and FC results.

    Returns: {"status": "ready_to_write|discarded|wilson_review", "article_type": "...", "reason": "..."}
    """
    vertente = item.get("vertente", "media_watch")
    media_audit = item.get("media_audit") or {}
    bias_verdict = item.get("bias_verdict") or {}
    bias_score = float(item.get("bias_score", 0.0))
    recommendation = media_audit.get("publish_recommendation", "")
    factos_correctos = media_audit.get("factos_correctos", True)
    bias_type = bias_verdict.get("bias_type", "none")
    omitted_facts = bias_verdict.get("omitted_facts", [])

    # ── MEDIA WATCH ──────────────────────────────────────────────────
    if vertente == "media_watch":
        # Explicit FC recommendation takes priority
        if recommendation == "expose":
            return {
                "status": "ready_to_write",
                "article_type": "expose",
                "reason": f"FC recomendou expose (bias_type={bias_type}, bias={bias_score:.2f})",
            }

        if recommendation == "omission":
            return {
                "status": "ready_to_write",
                "article_type": "omission",
                "reason": f"FC detectou omissao ({len(omitted_facts)} factos omitidos)",
            }

        if recommendation == "needs_review":
            return {
                "status": "wilson_review",
                "article_type": "",
                "reason": "FC marcou como ambiguo — precisa revisao humana",
            }

        # Heuristic: high bias even if FC said discard
        if bias_score > BIAS_EXPOSE_THRESHOLD and bias_type != "none":
            return {
                "status": "ready_to_write",
                "article_type": "expose",
                "reason": f"Bias alto detectado (score={bias_score:.2f}, type={bias_type}) apesar de FC recomendar discard",
            }

        # Heuristic: omitted facts present even if recommendation is discard
        if omitted_facts and len(omitted_facts) >= 2:
            return {
                "status": "ready_to_write",
                "article_type": "omission",
                "reason": f"{len(omitted_facts)} factos omitidos detectados",
            }

        # Default for media_watch: correct news without bias → discard
        return {
            "status": "discarded",
            "article_type": "",
            "reason": "Noticia dos media factualmente correcta e sem vies significativo — nao nos interessa",
        }

    # ── ALT-NEWS ─────────────────────────────────────────────────────
    elif vertente == "alt_news":
        if recommendation == "needs_review":
            return {
                "status": "wilson_review",
                "article_type": "",
                "reason": "Noticia alternativa ambigua — precisa revisao humana",
            }

        if recommendation == "discard":
            return {
                "status": "discarded",
                "article_type": "",
                "reason": "FC rejeitou noticia alternativa (sem fontes suficientes)",
            }

        # Alt-news verified → publish
        return {
            "status": "ready_to_write",
            "article_type": "alt_news",
            "reason": f"Noticia alternativa verificada (recommendation={recommendation})",
        }

    # ── EDITORIAL (Wilson's manual injections) ───────────────────────
    elif vertente == "editorial":
        if recommendation == "needs_review":
            return {
                "status": "wilson_review",
                "article_type": "",
                "reason": "Injecao editorial precisa de mais verificacao",
            }

        # Wilson submitted → respect priority, publish as editorial or fact_check
        article_type = "editorial"
        if recommendation == "fact_check":
            article_type = "fact_check"

        return {
            "status": "ready_to_write",
            "article_type": article_type,
            "reason": f"Injecao editorial do Wilson aprovada pelo FC (type={article_type})",
        }

    # ── FALLBACK ─────────────────────────────────────────────────────
    else:
        return {
            "status": "wilson_review",
            "article_type": "",
            "reason": f"Vertente desconhecida: {vertente}",
        }


def _apply_decision(supabase, item: dict, decision: dict) -> None:
    """Apply the editorial decision to the intake_queue item."""
    update = {
        "status": decision["status"],
    }

    if decision.get("article_type"):
        # Store article_type in metadata for the escritor to read
        metadata = item.get("metadata") or {}
        metadata["article_type"] = decision["article_type"]
        metadata["decisor_reason"] = decision["reason"]
        metadata["decisor_version"] = "v3-contra-media"
        update["metadata"] = metadata

    supabase.table("intake_queue").update(update).eq("id", item["id"]).execute()

    status_emoji = {
        "ready_to_write": "WRITE",
        "discarded": "DISCARD",
        "wilson_review": "REVIEW",
    }

    logger.info(
        "Decisor: [%s] '%s' → %s | %s",
        status_emoji.get(decision["status"], "?"),
        item.get("title", "")[:60],
        decision.get("article_type", "-"),
        decision["reason"][:80],
    )

    # If wilson_review, try to notify via Telegram
    if decision["status"] == "wilson_review" and TELEGRAM_BOT_TOKEN and WILSON_CHAT_ID:
        _notify_wilson(item, decision)


def _notify_wilson(item: dict, decision: dict) -> None:
    """Send Telegram notification to Wilson for review items."""
    try:
        import httpx
        msg = (
            f"📋 *Revisao necessaria*\n\n"
            f"*Titulo:* {item.get('title', '')[:100]}\n"
            f"*Area:* {item.get('area', '?')}\n"
            f"*Vertente:* {item.get('vertente', '?')}\n"
            f"*Motivo:* {decision['reason']}\n"
            f"*URL:* {item.get('url', 'n/a')}"
        )
        httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": WILSON_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        logger.warning("Decisor: falha ao notificar Wilson via Telegram: %s", e)


def _finalize_run(supabase, run_id, stats):
    """Update pipeline_runs with final stats."""
    if run_id:
        try:
            supabase.table("pipeline_runs").update({
                "status": "completed" if stats.get("errors", 0) == 0 else "completed_with_errors",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": stats.get("total", 0),
                "events_out": stats.get("ready_to_write", 0),
                "metadata": stats,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Decisor: falha ao actualizar pipeline_run: %s", e)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    result = run_editorial_decisor()
    print(f"\nResultado: {result}")
