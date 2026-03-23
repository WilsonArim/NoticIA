"""
Coverage Analyzer V3 — Detecta omissoes dos media.

Corre cada 6 horas. Cruza fontes media vs alternativas para encontrar
noticias que apenas fontes alternativas reportam (omissoes dos media).

Candidatos a omissao sao inseridos na intake_queue com vertente='media_watch'
e metadata.source_agent='coverage_analyzer' para serem auditados pelo FC.

Estrategia:
  1. Buscar raw_events das ultimas 24h agrupados por source_type
  2. Para cada evento alternativo, procurar cobertura mainstream por keywords
  3. Se ZERO cobertura mainstream → candidato a omissao
  4. Inserir candidatos na intake_queue para o FC auditar
"""
import hashlib
import logging
import os
import re
from datetime import datetime, timezone, timedelta

from supabase import create_client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
LOOKBACK_HOURS = int(os.getenv("COVERAGE_LOOKBACK_HOURS", "24"))
MIN_ALT_EVENTS_FOR_SIGNAL = int(os.getenv("COVERAGE_MIN_ALT_EVENTS", "2"))
MAX_CANDIDATES_PER_RUN = int(os.getenv("COVERAGE_MAX_CANDIDATES", "10"))


def _normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    return re.sub(r"\s+", " ", title.lower().strip())


def _title_hash(title: str) -> str:
    """MD5 of normalized title."""
    return hashlib.md5(_normalize_title(title).encode()).hexdigest()


def _extract_keywords(title: str) -> set[str]:
    """Extract meaningful keywords from a title for matching."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must",
        "in", "on", "at", "to", "for", "with", "from", "by", "of", "about",
        "and", "or", "but", "not", "no", "if", "then", "so", "as",
        "o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das",
        "em", "no", "na", "nos", "nas", "por", "para", "com", "sem",
        "e", "ou", "mas", "que", "se", "como", "mais", "menos",
        "este", "esta", "estes", "estas", "esse", "essa",
    }
    words = re.findall(r"\b[a-zA-ZÀ-ÿ]{3,}\b", title.lower())
    return {w for w in words if w not in stop_words}


def _keywords_overlap(kw1: set[str], kw2: set[str]) -> float:
    """Calculate keyword overlap ratio (Jaccard-like)."""
    if not kw1 or not kw2:
        return 0.0
    intersection = kw1 & kw2
    union = kw1 | kw2
    return len(intersection) / len(union)


def run_coverage_analysis() -> dict:
    """Detect omissions: events reported by alternative sources but not by mainstream media.

    Returns stats dict.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Coverage Analyzer: SUPABASE_URL ou SERVICE_KEY em falta")
        return {}

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # --- pipeline_runs logging ---
    run_id = None
    try:
        run_row = supabase.table("pipeline_runs").insert({
            "stage": "coverage_analyzer",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events_in": 0,
            "events_out": 0,
        }).execute()
        run_id = run_row.data[0]["id"] if run_row.data else None
    except Exception as e:
        logger.warning("Coverage Analyzer: falha ao criar pipeline_run: %s", e)

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).isoformat()
    stats = {
        "media_events": 0,
        "alt_events": 0,
        "candidates_found": 0,
        "candidates_inserted": 0,
        "already_in_queue": 0,
        "errors": 0,
    }

    try:
        # 1. Fetch recent alternative events
        alt_result = (
            supabase.table("raw_events")
            .select("id, title, content, url, source_collector, published_at")
            .eq("source_type", "alternative")
            .gte("created_at", cutoff)
            .order("published_at", desc=True)
            .limit(100)
            .execute()
        )
        alt_events = alt_result.data or []
        stats["alt_events"] = len(alt_events)

        if not alt_events:
            logger.info("Coverage Analyzer: sem eventos alternativos nas ultimas %dh", LOOKBACK_HOURS)
            _finalize_run(supabase, run_id, stats)
            return stats

        # 2. Fetch recent media events (for comparison)
        media_result = (
            supabase.table("raw_events")
            .select("title")
            .eq("source_type", "media")
            .gte("created_at", cutoff)
            .limit(500)
            .execute()
        )
        media_events = media_result.data or []
        stats["media_events"] = len(media_events)

        # 3. Build keyword index from media events
        media_keyword_sets = []
        for me in media_events:
            kw = _extract_keywords(me.get("title", ""))
            if kw:
                media_keyword_sets.append(kw)

        # 4. Fetch existing title_hashes in intake_queue to avoid duplicates
        alt_hashes = [_title_hash(e.get("title", "")) for e in alt_events]
        existing = set()
        if alt_hashes:
            try:
                existing_result = (
                    supabase.table("intake_queue")
                    .select("title_hash")
                    .in_("title_hash", alt_hashes[:100])
                    .execute()
                )
                existing = {r["title_hash"] for r in (existing_result.data or []) if r.get("title_hash")}
            except Exception:
                pass

        # 5. Find alternative events with NO mainstream coverage
        candidates = []
        for alt_ev in alt_events:
            alt_title = alt_ev.get("title", "")
            alt_kw = _extract_keywords(alt_title)

            if not alt_kw or len(alt_kw) < 2:
                continue

            # Check if any media event covers the same topic
            has_coverage = False
            for media_kw in media_keyword_sets:
                overlap = _keywords_overlap(alt_kw, media_kw)
                if overlap >= 0.3:  # 30% keyword overlap = likely same topic
                    has_coverage = True
                    break

            if not has_coverage:
                # Check if already in intake_queue
                t_hash = _title_hash(alt_title)
                if t_hash in existing:
                    stats["already_in_queue"] += 1
                    continue

                candidates.append({
                    "event": alt_ev,
                    "title_hash": t_hash,
                    "keywords": alt_kw,
                })

        stats["candidates_found"] = len(candidates)
        logger.info(
            "Coverage Analyzer: %d alt events, %d media events, %d candidates sem cobertura",
            stats["alt_events"], stats["media_events"], stats["candidates_found"],
        )

        # 6. Insert top candidates into intake_queue for FC audit
        inserted = 0
        for cand in candidates[:MAX_CANDIDATES_PER_RUN]:
            try:
                ev = cand["event"]
                row = {
                    "title": ev.get("title", "")[:500],
                    "content": (ev.get("content") or "")[:5000],
                    "url": ev.get("url", ""),
                    "area": "geopolitica",  # default area; dispatcher can reclassify
                    "score": 0.7,
                    "priority": "p2",
                    "status": "auditor_approved",  # skip dispatcher, go direct to FC
                    "language": "pt",
                    "title_hash": cand["title_hash"],
                    "vertente": "media_watch",  # treated as media omission
                    "metadata": {
                        "source_collector": ev.get("source_collector", "telegram"),
                        "source_agent": "coverage_analyzer",
                        "source_type": "alternative",
                        "coverage_analysis": {
                            "media_events_checked": stats["media_events"],
                            "keyword_overlap": 0.0,
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                        },
                        "dispatcher_version": "v3-coverage-analyzer",
                    },
                }

                supabase.table("intake_queue").insert(row).execute()
                inserted += 1

            except Exception as e:
                logger.warning("Coverage Analyzer: falha ao inserir candidato: %s", e)
                stats["errors"] += 1

        stats["candidates_inserted"] = inserted
        logger.info(
            "Coverage Analyzer concluido: candidatos=%d, inseridos=%d, ja_na_queue=%d",
            stats["candidates_found"], inserted, stats["already_in_queue"],
        )

    except Exception as e:
        logger.error("Coverage Analyzer falhou: %s", e)
        stats["errors"] += 1

    _finalize_run(supabase, run_id, stats)
    return stats


def _finalize_run(supabase, run_id, stats):
    if run_id:
        try:
            supabase.table("pipeline_runs").update({
                "status": "completed" if stats.get("errors", 0) == 0 else "completed_with_errors",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": stats.get("alt_events", 0),
                "events_out": stats.get("candidates_inserted", 0),
                "metadata": stats,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Coverage Analyzer: falha ao actualizar pipeline_run: %s", e)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    result = run_coverage_analysis()
    print(f"\nResultado: {result}")
