"""
Engenheiro de Pipeline V3 — Watchdog autónomo do NoticIA Contra-Media.

O agente mais experiente da pipeline. Monitoriza cada estágio do fluxo
de dados em tempo real, detecta anomalias antes de se tornarem falhas,
e regista tudo com detalhe cirúrgico.

Fluxo V3 monitorizado:
  Collectors (RSS/GDELT/Telegram) → raw_events (com source_type)
    → Dispatcher V3 (dedup + filtro + batch LLM + vertente routing)
    → intake_queue (status=auditor_approved, com vertente)
    → Fact-Checker V3 Dual-Mode (media_audit / alt_news / editorial)
    → intake_queue (status=approved, com bias_verdict + media_audit)
    → Decisor Editorial (gate determinístico)
    → intake_queue (status=ready_to_write / discarded / wilson_review)
    → Escritor V3 (6 templates: exposé, omissão, alt_news, fact_check, editorial, standard)
    → articles (status=published, com article_type)

  Coverage Analyzer (cada 6h): cruza fontes alt vs media, detecta omissões

Executa a cada 30 minutos via scheduler. Cada execução:
  1. Sonda cada estágio (contagens, idades, erros, métricas V3)
  2. Calcula métricas de saúde (throughput, latência, taxas de erro/descarte)
  3. Detecta anomalias (estágios parados, backlogs, flood-waits, V3 gaps)
  4. Regista relatório completo em pipeline_runs (stage='pipeline_health')
  5. Alerta via Telegram se encontrar problemas críticos
  6. Actualiza o Diário de Bordo com resumo diário (1x/dia às 00:xx)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta

import httpx
from supabase import create_client

logger = logging.getLogger("engenheiro-pipeline")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8657227084:AAEVyu8IJr4u7dV0oK7QnTeab-jMvuf5Bg0")
ALERT_CHAT_ID = os.getenv("TELEGRAM_ALERT_CHAT_ID", "1353134241")
DIARIO_PATH = os.path.expanduser("~/noticia/DIARIO-DE-BORDO.md")

# ── Limiares de alerta ───────────────────────────────────────────────────

THRESHOLDS = {
    "raw_events_min_1h": 10,         # mínimo raw_events novos por hora
    "intake_approved_min_2h": 3,     # mínimo aprovados pelo dispatcher em 2h
    "articles_min_6h": 1,            # mínimo artigos publicados em 6h
    "intake_backlog_max": 200,       # máximo items pendentes na intake_queue
    "stale_approved_hours": 4,       # horas máx. sem fact-check após aprovação
    "stale_fact_checked_hours": 4,   # horas máx. sem decisão após fact-check
    "stale_ready_write_hours": 3,    # horas máx. sem escrita após decisor V3
    "error_rate_max": 0.5,           # taxa de erro máxima (50%)
    "discard_rate_warning": 0.90,    # alerta se >90% descartado (pipeline inútil)
    "discard_rate_low_warning": 0.10, # alerta se <10% descartado (decisor não funciona)
    "wilson_review_max": 20,         # máximo items à espera de Wilson
    "coverage_max_hours_since": 8,   # horas máx. sem corrida do coverage analyzer
}


# ── Sondas de estágio ────────────────────────────────────────────────────

def _probe_collectors(sb) -> dict:
    """Sonda estágio 1: Collectors → raw_events (com source_type V3)."""
    now = datetime.now(timezone.utc)
    h1 = (now - timedelta(hours=1)).isoformat()
    h6 = (now - timedelta(hours=6)).isoformat()

    # raw_events na última hora
    r1 = sb.table("raw_events").select("id", count="exact") \
        .gte("created_at", h1).execute()
    recent_1h = r1.count or 0

    # raw_events nas últimas 6h por source_collector
    by_source = {}
    by_source_type = {}
    try:
        r6 = sb.table("raw_events").select("source_collector, source_type") \
            .gte("created_at", h6).execute()
        for row in (r6.data or []):
            src = row.get("source_collector", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
            stype = row.get("source_type", "unknown")
            by_source_type[stype] = by_source_type.get(stype, 0) + 1
    except Exception:
        by_source = {}
        by_source_type = {}

    # Total não-processados
    unprocessed = sb.table("raw_events").select("id", count="exact") \
        .eq("processed", False).execute()

    return {
        "raw_events_1h": recent_1h,
        "raw_events_by_source_6h": by_source,
        "raw_events_by_source_type_6h": by_source_type,
        "raw_events_unprocessed": unprocessed.count or 0,
        "status": "healthy" if recent_1h >= THRESHOLDS["raw_events_min_1h"] else "degraded",
    }


def _probe_dispatcher(sb) -> dict:
    """Sonda estágio 2: Dispatcher V3 → intake_queue (com vertente routing)."""
    now = datetime.now(timezone.utc)
    h2 = (now - timedelta(hours=2)).isoformat()

    # Aprovados nas últimas 2h
    approved = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "auditor_approved") \
        .gte("created_at", h2).execute()
    recent_approved = approved.count or 0

    # Rejeitados nas últimas 2h
    rejected = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "auditor_failed") \
        .gte("created_at", h2).execute()
    recent_rejected = rejected.count or 0

    total = recent_approved + recent_rejected
    reject_rate = recent_rejected / total if total > 0 else 0

    # V3: distribuição por vertente (últimas 2h)
    by_vertente = {}
    try:
        v_result = sb.table("intake_queue").select("vertente") \
            .gte("created_at", h2).execute()
        for row in (v_result.data or []):
            v = row.get("vertente", "unknown") or "unknown"
            by_vertente[v] = by_vertente.get(v, 0) + 1
    except Exception:
        by_vertente = {}

    return {
        "approved_2h": recent_approved,
        "rejected_2h": recent_rejected,
        "reject_rate": round(reject_rate, 2),
        "by_vertente_2h": by_vertente,
        "status": "healthy" if recent_approved >= THRESHOLDS["intake_approved_min_2h"] else "degraded",
    }


def _probe_fact_checker(sb) -> dict:
    """Sonda estágio 3: Fact-Checker V3 Dual-Mode (auditor_approved → approved)."""
    now = datetime.now(timezone.utc)
    h2 = (now - timedelta(hours=2)).isoformat()
    stale_cutoff = (now - timedelta(hours=THRESHOLDS["stale_approved_hours"])).isoformat()

    # Aprovados pelo FC nas últimas 2h
    fc_approved = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "approved") \
        .gte("created_at", h2).execute()

    # Rejeitados pelo FC nas últimas 2h
    fc_rejected = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "fact_check") \
        .gte("created_at", h2).execute()

    # Items parados em auditor_approved há demasiado tempo
    stale = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "auditor_approved") \
        .lte("created_at", stale_cutoff).execute()

    # V3: verificar se bias_verdict e media_audit estão a ser preenchidos
    bias_filled = 0
    media_audit_filled = 0
    try:
        recent_approved = sb.table("intake_queue").select("bias_verdict, media_audit") \
            .eq("status", "approved") \
            .gte("created_at", h2) \
            .limit(50).execute()
        for row in (recent_approved.data or []):
            if row.get("bias_verdict"):
                bias_filled += 1
            if row.get("media_audit"):
                media_audit_filled += 1
    except Exception:
        pass

    fc_approved_count = fc_approved.count or 0

    return {
        "fc_approved_2h": fc_approved_count,
        "fc_rejected_2h": fc_rejected.count or 0,
        "stale_awaiting_fc": stale.count or 0,
        "v3_bias_verdict_filled": bias_filled,
        "v3_media_audit_filled": media_audit_filled,
        "v3_fields_healthy": bias_filled > 0 if fc_approved_count > 0 else True,
        "status": "degraded" if (stale.count or 0) > 10 else "healthy",
    }


def _probe_editorial_decisor(sb) -> dict:
    """Sonda estágio 4 (V3): Decisor Editorial (approved → ready_to_write/discarded/wilson_review)."""
    now = datetime.now(timezone.utc)
    h2 = (now - timedelta(hours=2)).isoformat()
    h24 = (now - timedelta(hours=24)).isoformat()

    # Items decididos nas últimas 2h por status de saída
    ready = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "ready_to_write") \
        .gte("created_at", h2).execute()

    discarded = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "discarded") \
        .gte("created_at", h2).execute()

    wilson_review = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "wilson_review") \
        .gte("created_at", h2).execute()

    # Total pendentes de Wilson (acumulado)
    wilson_total = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "wilson_review").execute()

    # Decisões nas últimas 24h por article_type
    by_article_type = {}
    try:
        decisions = sb.table("intake_queue").select("metadata") \
            .eq("status", "ready_to_write") \
            .gte("created_at", h24) \
            .limit(100).execute()
        for row in (decisions.data or []):
            meta = row.get("metadata") or {}
            atype = meta.get("article_type", "unknown")
            by_article_type[atype] = by_article_type.get(atype, 0) + 1
    except Exception:
        pass

    ready_count = ready.count or 0
    discarded_count = discarded.count or 0
    total_decided = ready_count + discarded_count + (wilson_review.count or 0)
    discard_rate = discarded_count / total_decided if total_decided > 0 else 0

    # Pipeline_runs do decisor
    decisor_runs = 0
    try:
        dr = sb.table("pipeline_runs").select("id", count="exact") \
            .eq("stage", "editorial_decisor") \
            .gte("started_at", h2).execute()
        decisor_runs = dr.count or 0
    except Exception:
        pass

    return {
        "ready_to_write_2h": ready_count,
        "discarded_2h": discarded_count,
        "wilson_review_2h": wilson_review.count or 0,
        "wilson_review_total": wilson_total.count or 0,
        "discard_rate_2h": round(discard_rate, 2),
        "by_article_type_24h": by_article_type,
        "decisor_runs_2h": decisor_runs,
        "status": "healthy" if decisor_runs > 0 else "degraded",
    }


def _probe_escritor(sb) -> dict:
    """Sonda estágio 5 (V3): Escritor V3 (ready_to_write → articles published)."""
    now = datetime.now(timezone.utc)
    h6 = (now - timedelta(hours=6)).isoformat()
    stale_cutoff = (now - timedelta(hours=THRESHOLDS["stale_ready_write_hours"])).isoformat()

    # Artigos publicados nas últimas 6h
    published = sb.table("articles").select("id", count="exact") \
        .gte("created_at", h6).execute()

    # V3: artigos por article_type nas últimas 24h
    h24 = (now - timedelta(hours=24)).isoformat()
    by_type = {}
    try:
        arts = sb.table("articles").select("article_type") \
            .gte("created_at", h24).execute()
        for row in (arts.data or []):
            atype = row.get("article_type", "standard") or "standard"
            by_type[atype] = by_type.get(atype, 0) + 1
    except Exception:
        pass

    # Items parados em ready_to_write (V3) ou approved (backward compat)
    stale_ready = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "ready_to_write") \
        .lte("created_at", stale_cutoff).execute()

    stale_approved = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "approved") \
        .lte("created_at", stale_cutoff).execute()

    return {
        "articles_published_6h": published.count or 0,
        "articles_by_type_24h": by_type,
        "stale_ready_to_write": stale_ready.count or 0,
        "stale_awaiting_writer": (stale_ready.count or 0) + (stale_approved.count or 0),
        "status": "healthy" if (published.count or 0) >= THRESHOLDS["articles_min_6h"] else "degraded",
    }


def _probe_coverage_analyzer(sb) -> dict:
    """Sonda estágio V3: Coverage Analyzer (detector de omissões)."""
    now = datetime.now(timezone.utc)
    h24 = (now - timedelta(hours=24)).isoformat()

    # Última corrida do coverage_analyzer
    last_run = None
    hours_since = None
    try:
        lr = sb.table("pipeline_runs").select("started_at, metadata, status") \
            .eq("stage", "coverage_analyzer") \
            .order("started_at", desc=True) \
            .limit(1).execute()
        if lr.data:
            last_run = lr.data[0]
            started = datetime.fromisoformat(last_run["started_at"].replace("Z", "+00:00"))
            hours_since = (now - started).total_seconds() / 3600
    except Exception:
        pass

    # Candidatos inseridos nas últimas 24h (source_agent=coverage_analyzer)
    candidates_24h = 0
    try:
        cands = sb.table("intake_queue").select("id", count="exact") \
            .gte("created_at", h24).execute()
        # Filtrar por metadata.source_agent - Supabase não suporta filtro JSONB directo
        # Vamos contar as corridas do coverage_analyzer e somar events_out
        runs = sb.table("pipeline_runs").select("events_out") \
            .eq("stage", "coverage_analyzer") \
            .gte("started_at", h24).execute()
        candidates_24h = sum(r.get("events_out", 0) for r in (runs.data or []))
    except Exception:
        pass

    status = "healthy"
    if hours_since is not None and hours_since > THRESHOLDS["coverage_max_hours_since"]:
        status = "degraded"
    elif hours_since is None:
        status = "unknown"

    return {
        "last_run": last_run.get("started_at") if last_run else None,
        "hours_since_last_run": round(hours_since, 1) if hours_since is not None else None,
        "last_status": last_run.get("status") if last_run else None,
        "candidates_24h": candidates_24h,
        "status": status,
    }


def _probe_backlog(sb) -> dict:
    """Sonda geral: backlog e filas (V3 com novos statuses)."""
    statuses = [
        "pending", "auditor_approved", "approved", "auditor_failed",
        "fact_check", "ready_to_write", "discarded", "wilson_review",
    ]
    counts = {}
    for status in statuses:
        r = sb.table("intake_queue").select("id", count="exact") \
            .eq("status", status).execute()
        counts[status] = r.count or 0

    total_backlog = (
        counts["pending"] + counts["auditor_approved"] +
        counts["approved"] + counts["ready_to_write"]
    )

    return {
        "queue_by_status": counts,
        "total_backlog": total_backlog,
        "total_discarded": counts["discarded"],
        "total_wilson_review": counts["wilson_review"],
        "status": "degraded" if total_backlog > THRESHOLDS["intake_backlog_max"] else "healthy",
    }


# ── Motor de diagnóstico V3 ──────────────────────────────────────────────

def _diagnose(probes: dict) -> list[dict]:
    """Analisa sondas e gera diagnósticos com severidade (V3)."""
    issues = []

    # ─── Collectors ───
    coll = probes["collectors"]
    if coll["raw_events_1h"] == 0:
        issues.append({
            "severity": "critical",
            "stage": "collectors",
            "msg": "ZERO raw_events na última hora — todos os collectors podem estar parados",
            "action": "Verificar RSS collector (scheduler), Telegram collector (flood-wait?), GDELT (429s?)",
        })
    elif coll["status"] == "degraded":
        issues.append({
            "severity": "warning",
            "stage": "collectors",
            "msg": f"Apenas {coll['raw_events_1h']} raw_events na última hora (mín: {THRESHOLDS['raw_events_min_1h']})",
            "action": "Verificar se algum collector está com erros",
        })

    # Fontes em falta
    sources_6h = coll.get("raw_events_by_source_6h", {})
    if sources_6h and "rss" not in sources_6h:
        issues.append({
            "severity": "warning",
            "stage": "collectors",
            "msg": "RSS collector sem actividade nas últimas 6h",
            "action": "Verificar logs do pipeline container (collector_runner)",
        })
    if sources_6h and "telegram" not in sources_6h:
        issues.append({
            "severity": "info",
            "stage": "collectors",
            "msg": "Telegram collector sem actividade nas últimas 6h (pode ser flood-wait)",
            "action": "Verificar logs do telegram-collector container",
        })

    # V3: verificar source_type distribution
    by_stype = coll.get("raw_events_by_source_type_6h", {})
    if by_stype and not by_stype.get("media"):
        issues.append({
            "severity": "warning",
            "stage": "collectors",
            "msg": "ZERO eventos do tipo 'media' nas últimas 6h — pipeline não tem fontes mainstream para auditar",
            "action": "Verificar se collector_runner está a marcar source_type correctamente",
        })

    # ─── Dispatcher ───
    disp = probes["dispatcher"]
    if disp["approved_2h"] == 0 and coll["raw_events_unprocessed"] > 20:
        issues.append({
            "severity": "critical",
            "stage": "dispatcher",
            "msg": f"Dispatcher parado: 0 aprovados em 2h com {coll['raw_events_unprocessed']} raw_events pendentes",
            "action": "Verificar scheduler job 'dispatcher', logs de erro no pipeline container",
        })

    # V3: verificar distribuição de vertentes
    by_vertente = disp.get("by_vertente_2h", {})
    if by_vertente and not by_vertente.get("media_watch") and not by_vertente.get("alt_news"):
        issues.append({
            "severity": "warning",
            "stage": "dispatcher",
            "msg": "Nenhuma vertente media_watch ou alt_news nas últimas 2h — routing V3 pode não estar activo",
            "action": "Verificar se dispatcher.py está a propagar source_type → vertente",
        })

    # ─── Fact-Checker V3 ───
    fc = probes["fact_checker"]
    if fc["stale_awaiting_fc"] > 10:
        issues.append({
            "severity": "warning",
            "stage": "fact_checker",
            "msg": f"{fc['stale_awaiting_fc']} items à espera de fact-check há mais de {THRESHOLDS['stale_approved_hours']}h",
            "action": "Verificar scheduler job 'fact_checker', possível timeout ou erro de API",
        })

    # V3: bias_verdict e media_audit devem estar preenchidos
    if not fc["v3_fields_healthy"]:
        issues.append({
            "severity": "warning",
            "stage": "fact_checker",
            "msg": f"Campos V3 vazios: bias_verdict={fc['v3_bias_verdict_filled']}, media_audit={fc['v3_media_audit_filled']} (de {fc['fc_approved_2h']} aprovados)",
            "action": "FC pode não estar a gravar bias_verdict/media_audit — verificar _apply_verdict() em fact_checker.py",
        })

    # ─── Decisor Editorial V3 ───
    decisor = probes["editorial_decisor"]
    if decisor["decisor_runs_2h"] == 0 and fc["fc_approved_2h"] > 0:
        issues.append({
            "severity": "warning",
            "stage": "editorial_decisor",
            "msg": "Decisor editorial sem corridas nas últimas 2h, mas FC está a aprovar items",
            "action": "Verificar scheduler job 'editorial_decisor', possível erro de import ou excepção",
        })

    # Taxa de descarte anormal
    if decisor["discard_rate_2h"] > THRESHOLDS["discard_rate_warning"]:
        issues.append({
            "severity": "warning",
            "stage": "editorial_decisor",
            "msg": f"Taxa de descarte {decisor['discard_rate_2h']*100:.0f}% (>90%) — pipeline pode estar a descartar tudo",
            "action": "Verificar lógica do decisor, thresholds de bias, ou se FC está a retornar bias_type='none' em tudo",
        })
    elif 0 < decisor["discard_rate_2h"] < THRESHOLDS["discard_rate_low_warning"] and decisor["discarded_2h"] + decisor["ready_to_write_2h"] > 5:
        issues.append({
            "severity": "info",
            "stage": "editorial_decisor",
            "msg": f"Taxa de descarte {decisor['discard_rate_2h']*100:.0f}% (<10%) — quase tudo passa para escrita",
            "action": "Pode ser normal no início. Se persistir, o FC pode estar a encontrar viés em tudo",
        })

    # Wilson review acumulado
    if decisor["wilson_review_total"] > THRESHOLDS["wilson_review_max"]:
        issues.append({
            "severity": "warning",
            "stage": "editorial_decisor",
            "msg": f"{decisor['wilson_review_total']} items à espera de revisão manual (máx: {THRESHOLDS['wilson_review_max']})",
            "action": "Avisar Wilson via Telegram para rever items pendentes",
        })

    # ─── Escritor V3 ───
    esc = probes["escritor"]
    if esc["articles_published_6h"] == 0:
        issues.append({
            "severity": "warning",
            "stage": "escritor",
            "msg": "ZERO artigos publicados nas últimas 6h",
            "action": "Verificar scheduler job 'escritor', backlog de ready_to_write items",
        })
    if esc["stale_awaiting_writer"] > 5:
        issues.append({
            "severity": "warning",
            "stage": "escritor",
            "msg": f"{esc['stale_awaiting_writer']} items à espera de escrita há mais de {THRESHOLDS['stale_ready_write_hours']}h",
            "action": "Escritor pode estar bloqueado ou com erros de LLM",
        })

    # ─── Coverage Analyzer V3 ───
    cov = probes["coverage_analyzer"]
    if cov["status"] == "degraded":
        issues.append({
            "severity": "warning",
            "stage": "coverage_analyzer",
            "msg": f"Coverage analyzer sem corrida há {cov['hours_since_last_run']:.0f}h (máx: {THRESHOLDS['coverage_max_hours_since']}h)",
            "action": "Verificar scheduler job 'coverage_analyzer', possível erro",
        })
    elif cov["status"] == "unknown":
        issues.append({
            "severity": "info",
            "stage": "coverage_analyzer",
            "msg": "Coverage analyzer nunca correu — aguardar primeira execução (intervalo: 6h)",
            "action": "Nenhuma acção necessária se pipeline foi reiniciado recentemente",
        })

    # ─── Backlog geral ───
    bl = probes["backlog"]
    if bl["total_backlog"] > THRESHOLDS["intake_backlog_max"]:
        issues.append({
            "severity": "warning",
            "stage": "pipeline",
            "msg": f"Backlog total de {bl['total_backlog']} items (máx: {THRESHOLDS['intake_backlog_max']})",
            "action": "Pipeline não está a processar ao ritmo da recolha",
        })

    return issues


# ── Alertas Telegram ──────────────────────────────────────────────────────

def _send_telegram_alert(issues: list[dict]) -> None:
    """Envia alerta Telegram para issues críticas e warnings."""
    critical = [i for i in issues if i["severity"] == "critical"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    if not critical and not warnings:
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"🔧 *Engenheiro Pipeline V3 — Relatório {now}*\n"]

    if critical:
        lines.append("🔴 *CRÍTICO:*")
        for i in critical:
            lines.append(f"  • [{i['stage']}] {i['msg']}")
        lines.append("")

    if warnings:
        lines.append("🟡 *AVISO:*")
        for i in warnings:
            lines.append(f"  • [{i['stage']}] {i['msg']}")

    msg = "\n".join(lines)

    try:
        httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": ALERT_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        logger.warning("Falha ao enviar alerta Telegram: %s", e)


# ── Registo em pipeline_runs ──────────────────────────────────────────────

def _log_health_report(sb, probes: dict, issues: list[dict], duration_ms: int) -> None:
    """Regista relatório completo na tabela pipeline_runs."""
    now = datetime.now(timezone.utc).isoformat()

    overall = "healthy"
    if any(i["severity"] == "critical" for i in issues):
        overall = "critical"
    elif any(i["severity"] == "warning" for i in issues):
        overall = "degraded"

    try:
        sb.table("pipeline_runs").insert({
            "stage": "pipeline_health",
            "status": "completed",
            "started_at": now,
            "completed_at": now,
            "events_in": probes["collectors"]["raw_events_1h"],
            "events_out": probes["escritor"]["articles_published_6h"],
            "metadata": {
                "agent": "engenheiro-pipeline",
                "version": "v3-contra-media",
                "overall_status": overall,
                "duration_ms": duration_ms,
                "probes": probes,
                "issues": issues,
                "thresholds": THRESHOLDS,
            },
        }).execute()
    except Exception as e:
        logger.warning("Falha ao registar health report: %s", e)


# ── Diário de Bordo (resumo diário) ──────────────────────────────────────

def _update_diario(probes: dict, issues: list[dict]) -> None:
    """Adiciona resumo diário ao Diário de Bordo (1x/dia, à meia-noite)."""
    now = datetime.now(timezone.utc)

    # Só escreve no diário entre 00:00 e 00:30 UTC
    if now.hour != 0 or now.minute > 30:
        return

    date_str = now.strftime("%Y-%m-%d")
    coll = probes["collectors"]
    disp = probes["dispatcher"]
    fc = probes["fact_checker"]
    decisor = probes["editorial_decisor"]
    esc = probes["escritor"]
    cov = probes["coverage_analyzer"]

    critical = [i for i in issues if i["severity"] == "critical"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    overall = "✅ Saudável"
    if critical:
        overall = "🔴 Crítico"
    elif warnings:
        overall = "🟡 Degradado"

    entry = f"""

---

## {date_str} — Relatório Diário do Engenheiro V3

**Estado geral:** {overall}

**Métricas (últimas horas):**
- raw_events/1h: {coll['raw_events_1h']} | não-processados: {coll['raw_events_unprocessed']}
- Fontes activas (6h): {', '.join(coll.get('raw_events_by_source_6h', {}).keys()) or 'nenhuma'}
- Source types (6h): {', '.join(f'{k}={v}' for k, v in coll.get('raw_events_by_source_type_6h', {}).items()) or 'n/a'}
- Dispatcher: {disp['approved_2h']} aprovados, {disp['rejected_2h']} rejeitados (2h)
- Vertentes (2h): {', '.join(f'{k}={v}' for k, v in disp.get('by_vertente_2h', {}).items()) or 'n/a'}
- FC V3: {fc['fc_approved_2h']} aprovados | bias_verdict: {fc['v3_bias_verdict_filled']} | media_audit: {fc['v3_media_audit_filled']}
- Decisor: {decisor['ready_to_write_2h']} → escrita, {decisor['discarded_2h']} descartados, {decisor['wilson_review_2h']} → Wilson
- Artigos publicados (6h): {esc['articles_published_6h']} | por tipo (24h): {', '.join(f'{k}={v}' for k, v in esc.get('articles_by_type_24h', {}).items()) or 'n/a'}
- Coverage Analyzer: última corrida {cov.get('hours_since_last_run', '?')}h atrás | candidatos (24h): {cov['candidates_24h']}
"""

    if critical or warnings:
        entry += "\n**Problemas detectados:**\n"
        for i in critical + warnings:
            icon = "🔴" if i["severity"] == "critical" else "🟡"
            entry += f"- {icon} [{i['stage']}] {i['msg']}\n"

    entry += f"\n*Registado automaticamente pelo engenheiro-pipeline V3 às {now.strftime('%H:%M UTC')}*\n"

    try:
        with open(DIARIO_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
        logger.info("Diário de bordo actualizado com relatório V3 de %s", date_str)
    except Exception as e:
        logger.warning("Falha ao actualizar diário de bordo: %s", e)


# ── Ponto de entrada ──────────────────────────────────────────────────────

def run_pipeline_health() -> None:
    """Executa check completo de saúde da pipeline V3. Chamado pelo scheduler."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Engenheiro: SUPABASE_URL / SUPABASE_SERVICE_KEY em falta")
        return

    import time
    start = time.monotonic()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info("═══ Engenheiro Pipeline V3 — Check de saúde %s ═══", now_str)

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # 1. Sondar cada estágio (V3: inclui decisor + coverage)
    try:
        probes = {
            "collectors": _probe_collectors(sb),
            "dispatcher": _probe_dispatcher(sb),
            "fact_checker": _probe_fact_checker(sb),
            "editorial_decisor": _probe_editorial_decisor(sb),
            "escritor": _probe_escritor(sb),
            "coverage_analyzer": _probe_coverage_analyzer(sb),
            "backlog": _probe_backlog(sb),
        }
    except Exception as e:
        logger.error("Engenheiro: falha ao sondar estágios — %s", e)
        return

    # 2. Diagnosticar
    issues = _diagnose(probes)

    duration_ms = int((time.monotonic() - start) * 1000)

    # 3. Log detalhado
    overall = "✅ SAUDÁVEL"
    if any(i["severity"] == "critical" for i in issues):
        overall = "🔴 CRÍTICO"
    elif any(i["severity"] == "warning" for i in issues):
        overall = "🟡 DEGRADADO"

    logger.info("  Collectors:    raw_events/1h=%d | unprocessed=%d | source_types=%s | %s",
                probes["collectors"]["raw_events_1h"],
                probes["collectors"]["raw_events_unprocessed"],
                probes["collectors"].get("raw_events_by_source_type_6h", {}),
                probes["collectors"]["status"])
    logger.info("  Dispatcher:    approved/2h=%d | rejected/2h=%d | vertentes=%s | %s",
                probes["dispatcher"]["approved_2h"],
                probes["dispatcher"]["rejected_2h"],
                probes["dispatcher"].get("by_vertente_2h", {}),
                probes["dispatcher"]["status"])
    logger.info("  Fact-Checker:  approved/2h=%d | stale=%d | bias_verdict=%d | media_audit=%d | %s",
                probes["fact_checker"]["fc_approved_2h"],
                probes["fact_checker"]["stale_awaiting_fc"],
                probes["fact_checker"]["v3_bias_verdict_filled"],
                probes["fact_checker"]["v3_media_audit_filled"],
                probes["fact_checker"]["status"])
    logger.info("  Decisor V3:    ready=%d | discarded=%d | wilson=%d | discard_rate=%.0f%% | runs=%d | %s",
                probes["editorial_decisor"]["ready_to_write_2h"],
                probes["editorial_decisor"]["discarded_2h"],
                probes["editorial_decisor"]["wilson_review_2h"],
                probes["editorial_decisor"]["discard_rate_2h"] * 100,
                probes["editorial_decisor"]["decisor_runs_2h"],
                probes["editorial_decisor"]["status"])
    logger.info("  Escritor:      published/6h=%d | stale=%d | by_type=%s | %s",
                probes["escritor"]["articles_published_6h"],
                probes["escritor"]["stale_awaiting_writer"],
                probes["escritor"].get("articles_by_type_24h", {}),
                probes["escritor"]["status"])
    logger.info("  Coverage:      last_run=%sh ago | candidates/24h=%d | %s",
                probes["coverage_analyzer"].get("hours_since_last_run", "?"),
                probes["coverage_analyzer"]["candidates_24h"],
                probes["coverage_analyzer"]["status"])
    logger.info("  Backlog:       total=%d | discarded=%d | wilson_review=%d | %s",
                probes["backlog"]["total_backlog"],
                probes["backlog"]["total_discarded"],
                probes["backlog"]["total_wilson_review"],
                probes["backlog"]["status"])
    logger.info("  Estado geral:  %s (%d issues, %dms)", overall, len(issues), duration_ms)

    for i in issues:
        if i["severity"] == "critical":
            logger.error("  🔴 [%s] %s → %s", i["stage"], i["msg"], i["action"])
        elif i["severity"] == "warning":
            logger.warning("  🟡 [%s] %s → %s", i["stage"], i["msg"], i["action"])
        else:
            logger.info("  ℹ️ [%s] %s", i["stage"], i["msg"])

    # 4. Registar em pipeline_runs
    _log_health_report(sb, probes, issues, duration_ms)

    # 5. Alertar via Telegram se necessário
    _send_telegram_alert(issues)

    # 6. Diário de bordo (1x/dia)
    _update_diario(probes, issues)

    logger.info("═══ Engenheiro Pipeline V3 — Check concluído em %dms ═══", duration_ms)
