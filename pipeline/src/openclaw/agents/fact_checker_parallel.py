"""
Fact-Checker Paralelo Sectorial V3 — 6 FCs em paralelo, vertente-aware.

V3: Cada item carrega uma 'vertente' (media_watch, alt_news, editorial)
que determina o modo do FC (auditoria media, verificacao rigorosa, ou editorial).
O routing por sector (area) mantem-se igual.

Sectores:
  fc-mundo:     geopolitica, politica_intl, diplomacia, defesa, defesa_estrategica
  fc-tech:      tecnologia, ciencia, energia, clima
  fc-portugal:  portugal, sociedade
  fc-economia:  economia, financas, crypto, regulacao
  fc-saude:     saude, direitos_humanos
  fc-justica:   desinformacao, crime_organizado

Frequencia: cada 25 min via scheduler_ollama.py
Modelo:     MODEL_FACTCHECKER (fallback: mistral-large-3:675b)
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from supabase import create_client

from openclaw.agents.fact_checker import (
    _check_item,
    _apply_verdict,
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    MODEL,
)

logger = logging.getLogger(__name__)

# Mapeamento sector -> areas
SECTOR_AREAS: dict[str, list[str]] = {
    "fc-mundo": ["geopolitica", "politica_intl", "diplomacia", "defesa", "defesa_estrategica"],
    "fc-tech": ["tecnologia", "ciencia", "energia", "clima"],
    "fc-portugal": ["portugal", "sociedade"],
    "fc-economia": ["economia", "financas", "crypto", "regulacao"],
    "fc-saude": ["saude", "direitos_humanos"],
    "fc-justica": ["desinformacao", "crime_organizado"],
}

ITEMS_PER_SECTOR = int(os.getenv("FC_ITEMS_PER_SECTOR", "10"))
MAX_WORKERS = int(os.getenv("FC_MAX_WORKERS", "6"))


def _run_sector(sector: str, areas: list[str]) -> dict:
    """Processa items de um sector especifico. Corre numa thread."""
    stats = {"sector": sector, "areas": areas, "fetched": 0, "approved": 0, "rejected": 0, "errors": 0}

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        result = (
            sb.table("intake_queue")
            .select("*")
            .eq("status", "auditor_approved")
            .in_("area", areas)
            .order("score", desc=True)
            .limit(ITEMS_PER_SECTOR)
            .execute()
        )

        items = result.data or []
        stats["fetched"] = len(items)

        if not items:
            logger.debug("FC [%s]: sem items para verificar", sector)
            return stats

        # V3: log vertente distribution
        vertentes = {}
        for it in items:
            v = it.get("vertente", "media_watch")
            vertentes[v] = vertentes.get(v, 0) + 1
        logger.info("FC [%s]: verificando %d items (areas: %s, vertentes: %s)", sector, len(items), ", ".join(areas), vertentes)

        for item in items:
            try:
                verdict = _check_item(item)
                _apply_verdict(sb, item, verdict)
                # V3: match approval logic in _apply_verdict — certainty >= 0.70 = approved
                certainty = float(verdict.get("certainty_score", 0))
                vertente = item.get("vertente", "media_watch")
                if vertente in ("media_watch", "alt_news", "editorial"):
                    if certainty >= 0.70:
                        stats["approved"] += 1
                    else:
                        stats["rejected"] += 1
                else:
                    if verdict.get("aprovado") and certainty >= 0.70:
                        stats["approved"] += 1
                    else:
                        stats["rejected"] += 1
            except Exception as e:
                logger.error("FC [%s] erro item %s: %s", sector, item.get("id", "?"), e)
                stats["errors"] += 1

    except Exception as e:
        logger.error("FC [%s] falha geral: %s", sector, e)
        stats["errors"] += 1

    return stats


def run_fact_checkers_parallel() -> dict:
    """Lanca os 6 fact-checkers sectoriais em paralelo."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("FC Paralelo: SUPABASE_URL ou SERVICE_KEY em falta")
        return {}

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    run_id = None
    try:
        run_row = sb.table("pipeline_runs").insert({
            "stage": "fact_checker",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events_in": 0,
            "events_out": 0,
        }).execute()
        run_id = run_row.data[0]["id"] if run_row.data else None
    except Exception as e:
        logger.warning("FC Paralelo: falha ao criar pipeline_run: %s", e)

    start_time = datetime.now(timezone.utc)
    all_stats: list[dict] = []

    logger.info(
        "=== FC Paralelo: lancando %d sectores (max %d workers, %d items/sector) ===",
        len(SECTOR_AREAS), MAX_WORKERS, ITEMS_PER_SECTOR,
    )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_run_sector, sector, areas): sector
            for sector, areas in SECTOR_AREAS.items()
        }

        for future in as_completed(futures):
            sector = futures[future]
            try:
                stats = future.result(timeout=300)
                all_stats.append(stats)
                logger.info(
                    "FC [%s] concluido: fetched=%d approved=%d rejected=%d errors=%d",
                    stats["sector"], stats["fetched"], stats["approved"],
                    stats["rejected"], stats["errors"],
                )
            except Exception as e:
                logger.error("FC [%s] timeout ou erro: %s", sector, e)
                all_stats.append({"sector": sector, "fetched": 0, "approved": 0, "rejected": 0, "errors": 1})

    total_in = sum(s["fetched"] for s in all_stats)
    total_out = sum(s["approved"] for s in all_stats)
    total_errors = sum(s["errors"] for s in all_stats)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    logger.info(
        "=== FC Paralelo concluido em %.0fs: total_in=%d total_approved=%d total_errors=%d ===",
        duration, total_in, total_out, total_errors,
    )

    if run_id:
        try:
            sb.table("pipeline_runs").update({
                "status": "completed" if total_errors == 0 else "completed_with_errors",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": total_in,
                "events_out": total_out,
                "metadata": {
                    "version": "v2-parallel-sectorial",
                    "sectors": all_stats,
                    "duration_seconds": round(duration, 1),
                    "max_workers": MAX_WORKERS,
                    "items_per_sector": ITEMS_PER_SECTOR,
                },
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("FC Paralelo: falha ao actualizar pipeline_run: %s", e)

    return {
        "total_in": total_in,
        "total_out": total_out,
        "total_errors": total_errors,
        "sectors": all_stats,
        "duration_seconds": round(duration, 1),
    }
