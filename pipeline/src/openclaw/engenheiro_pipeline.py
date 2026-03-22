"""
Engenheiro de Pipeline — Watchdog autónomo do NoticIA.

O agente mais experiente da pipeline. Monitoriza cada estágio do fluxo
de dados em tempo real, detecta anomalias antes de se tornarem falhas,
e regista tudo com detalhe cirúrgico.

Fluxo monitorizado:
  Collectors (RSS/GDELT/Telegram) → raw_events → Dispatcher → intake_queue
  → Fact-Checker → Escritor → articles (published)

Executa a cada 30 minutos via scheduler. Cada execução:
  1. Sonda cada estágio (contagens, idades, erros)
  2. Calcula métricas de saúde (throughput, latência, taxas de erro)
  3. Detecta anomalias (estágios parados, backlogs, flood-waits)
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
    "raw_events_min_1h": 10,       # mínimo raw_events novos por hora
    "intake_approved_min_2h": 3,   # mínimo aprovados pelo dispatcher em 2h
    "articles_min_6h": 1,          # mínimo artigos publicados em 6h
    "intake_backlog_max": 200,     # máximo items pendentes na intake_queue
    "stale_approved_hours": 4,     # horas máx. sem fact-check após aprovação
    "stale_fact_checked_hours": 4, # horas máx. sem escrita após fact-check
    "error_rate_max": 0.5,         # taxa de erro máxima (50%)
}


# ── Sondas de estágio ────────────────────────────────────────────────────

def _probe_collectors(sb) -> dict:
    """Sonda estágio 1: Collectors → raw_events."""
    now = datetime.now(timezone.utc)
    h1 = (now - timedelta(hours=1)).isoformat()
    h6 = (now - timedelta(hours=6)).isoformat()

    # raw_events na última hora
    r1 = sb.table("raw_events").select("id", count="exact") \
        .gte("created_at", h1).execute()
    recent_1h = r1.count or 0

    # raw_events nas últimas 6h por source_collector
    by_source = {}
    try:
        r6 = sb.table("raw_events").select("source_collector") \
            .gte("created_at", h6).execute()
        for row in (r6.data or []):
            src = row.get("source_collector", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
    except Exception:
        by_source = {}

    # Total não-processados
    unprocessed = sb.table("raw_events").select("id", count="exact") \
        .eq("processed", False).execute()

    return {
        "raw_events_1h": recent_1h,
        "raw_events_by_source_6h": by_source,
        "raw_events_unprocessed": unprocessed.count or 0,
        "status": "healthy" if recent_1h >= THRESHOLDS["raw_events_min_1h"] else "degraded",
    }


def _probe_dispatcher(sb) -> dict:
    """Sonda estágio 2: Dispatcher → intake_queue (auditor_approved)."""
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

    return {
        "approved_2h": recent_approved,
        "rejected_2h": recent_rejected,
        "reject_rate": round(reject_rate, 2),
        "status": "healthy" if recent_approved >= THRESHOLDS["intake_approved_min_2h"] else "degraded",
    }


def _probe_fact_checker(sb) -> dict:
    """Sonda estágio 3: Fact-Checker (auditor_approved → approved)."""
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

    return {
        "fc_approved_2h": fc_approved.count or 0,
        "fc_rejected_2h": fc_rejected.count or 0,
        "stale_awaiting_fc": stale.count or 0,
        "status": "degraded" if (stale.count or 0) > 10 else "healthy",
    }


def _probe_escritor(sb) -> dict:
    """Sonda estágio 4: Escritor (approved → articles published)."""
    now = datetime.now(timezone.utc)
    h6 = (now - timedelta(hours=6)).isoformat()
    stale_cutoff = (now - timedelta(hours=THRESHOLDS["stale_fact_checked_hours"])).isoformat()

    # Artigos publicados nas últimas 6h
    published = sb.table("articles").select("id", count="exact") \
        .gte("created_at", h6).execute()

    # Items aprovados pelo FC mas parados (sem escrita)
    stale = sb.table("intake_queue").select("id", count="exact") \
        .eq("status", "approved") \
        .lte("created_at", stale_cutoff).execute()

    return {
        "articles_published_6h": published.count or 0,
        "stale_awaiting_writer": stale.count or 0,
        "status": "healthy" if (published.count or 0) >= THRESHOLDS["articles_min_6h"] else "degraded",
    }


def _probe_backlog(sb) -> dict:
    """Sonda geral: backlog e filas."""
    statuses = ["pending", "auditor_approved", "approved", "auditor_failed", "fact_check"]
    counts = {}
    for status in statuses:
        r = sb.table("intake_queue").select("id", count="exact") \
            .eq("status", status).execute()
        counts[status] = r.count or 0

    total_backlog = counts["pending"] + counts["auditor_approved"] + counts["approved"]

    return {
        "queue_by_status": counts,
        "total_backlog": total_backlog,
        "status": "degraded" if total_backlog > THRESHOLDS["intake_backlog_max"] else "healthy",
    }


# ── Motor de diagnóstico ─────────────────────────────────────────────────

def _diagnose(probes: dict) -> list[dict]:
    """Analisa sondas e gera diagnósticos com severidade."""
    issues = []

    # Collectors parados
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
        # Telegram pode estar em flood-wait legítimo, warning apenas
        issues.append({
            "severity": "info",
            "stage": "collectors",
            "msg": "Telegram collector sem actividade nas últimas 6h (pode ser flood-wait)",
            "action": "Verificar logs do telegram-collector container",
        })

    # Dispatcher parado
    disp = probes["dispatcher"]
    if disp["approved_2h"] == 0 and coll["raw_events_unprocessed"] > 20:
        issues.append({
            "severity": "critical",
            "stage": "dispatcher",
            "msg": f"Dispatcher parado: 0 aprovados em 2h com {coll['raw_events_unprocessed']} raw_events pendentes",
            "action": "Verificar scheduler job 'dispatcher', logs de erro no pipeline container",
        })

    # Fact-checker com backlog
    fc = probes["fact_checker"]
    if fc["stale_awaiting_fc"] > 10:
        issues.append({
            "severity": "warning",
            "stage": "fact_checker",
            "msg": f"{fc['stale_awaiting_fc']} items à espera de fact-check há mais de {THRESHOLDS['stale_approved_hours']}h",
            "action": "Verificar scheduler job 'fact_checker', possível timeout ou erro de API",
        })

    # Escritor parado
    esc = probes["escritor"]
    if esc["articles_published_6h"] == 0:
        issues.append({
            "severity": "warning",
            "stage": "escritor",
            "msg": "ZERO artigos publicados nas últimas 6h",
            "action": "Verificar scheduler job 'escritor', backlog de approved items",
        })
    if esc["stale_awaiting_writer"] > 5:
        issues.append({
            "severity": "warning",
            "stage": "escritor",
            "msg": f"{esc['stale_awaiting_writer']} items fact-checked à espera de escrita há mais de {THRESHOLDS['stale_fact_checked_hours']}h",
            "action": "Escritor pode estar bloqueado ou com erros de LLM",
        })

    # Backlog excessivo
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
    lines = [f"🔧 *Engenheiro Pipeline — Relatório {now}*\n"]

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
    esc = probes["escritor"]

    critical = [i for i in issues if i["severity"] == "critical"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    overall = "✅ Saudável"
    if critical:
        overall = "🔴 Crítico"
    elif warnings:
        overall = "🟡 Degradado"

    entry = f"""

---

## {date_str} — Relatório Diário do Engenheiro de Pipeline

**Estado geral:** {overall}

**Métricas (últimas horas):**
- raw_events/1h: {coll['raw_events_1h']} | não-processados: {coll['raw_events_unprocessed']}
- Fontes activas (6h): {', '.join(coll.get('raw_events_by_source_6h', {}).keys()) or 'nenhuma'}
- Dispatcher: {disp['approved_2h']} aprovados, {disp['rejected_2h']} rejeitados (2h)
- Artigos publicados (6h): {esc['articles_published_6h']}
"""

    if critical or warnings:
        entry += "\n**Problemas detectados:**\n"
        for i in critical + warnings:
            icon = "🔴" if i["severity"] == "critical" else "🟡"
            entry += f"- {icon} [{i['stage']}] {i['msg']}\n"

    entry += f"\n*Registado automaticamente pelo engenheiro-pipeline às {now.strftime('%H:%M UTC')}*\n"

    try:
        with open(DIARIO_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
        logger.info("Diário de bordo actualizado com relatório de %s", date_str)
    except Exception as e:
        logger.warning("Falha ao actualizar diário de bordo: %s", e)


# ── Ponto de entrada ──────────────────────────────────────────────────────

def run_pipeline_health() -> None:
    """Executa check completo de saúde da pipeline. Chamado pelo scheduler."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Engenheiro: SUPABASE_URL / SUPABASE_SERVICE_KEY em falta")
        return

    import time
    start = time.monotonic()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info("═══ Engenheiro Pipeline — Check de saúde %s ═══", now_str)

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # 1. Sondar cada estágio
    try:
        probes = {
            "collectors": _probe_collectors(sb),
            "dispatcher": _probe_dispatcher(sb),
            "fact_checker": _probe_fact_checker(sb),
            "escritor": _probe_escritor(sb),
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

    logger.info("  Collectors:    raw_events/1h=%d | unprocessed=%d | %s",
                probes["collectors"]["raw_events_1h"],
                probes["collectors"]["raw_events_unprocessed"],
                probes["collectors"]["status"])
    logger.info("  Dispatcher:    approved/2h=%d | rejected/2h=%d | %s",
                probes["dispatcher"]["approved_2h"],
                probes["dispatcher"]["rejected_2h"],
                probes["dispatcher"]["status"])
    logger.info("  Fact-Checker:  approved/2h=%d | stale=%d | %s",
                probes["fact_checker"]["fc_approved_2h"],
                probes["fact_checker"]["stale_awaiting_fc"],
                probes["fact_checker"]["status"])
    logger.info("  Escritor:      published/6h=%d | stale=%d | %s",
                probes["escritor"]["articles_published_6h"],
                probes["escritor"]["stale_awaiting_writer"],
                probes["escritor"]["status"])
    logger.info("  Backlog:       total=%d | %s",
                probes["backlog"]["total_backlog"],
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

    logger.info("═══ Engenheiro Pipeline — Check concluído em %dms ═══", duration_ms)
