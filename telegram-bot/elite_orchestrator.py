"""
Elite Orchestrator — Comando e Controlo da Equipa de Elite V2
==============================================================
State machine que coordena Director → Reporter → FC Forense → Escritor.
Gere transições de estado via Supabase. Envia updates ao Wilson via Telegram.

Activado pelo bot.py quando Wilson diz "/investiga X".
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timezone

from supabase import create_client
from openai import OpenAI

from elite_reporter import run_elite_reporter
from elite_fact_checker import run_elite_fact_checker
from elite_writer import run_elite_writer

logger = logging.getLogger("elite.orchestrator")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL = os.getenv("MODEL_ELITE_DIRECTOR", os.getenv("MODEL_EDITOR_CHEFE", "cogito-2.1:671b"))


DIRECTOR_SYSTEM_PROMPT = """You are the Director of the NoticIA Elite Investigation Team.
Your job is to decompose a user's investigation request into specific, actionable OSINT research tasks.

Each task should be a focused question that can be answered through web search, public records, or official documents.

RULES:
1. Decompose into 4-8 specific tasks (not too few, not too many)
2. Each task should target a DIFFERENT aspect of the investigation
3. Tasks should be ordered logically (establish basics first, then deeper investigation)
4. Include tasks for counter-narratives and opposing perspectives
5. Include a task specifically for financial/market impact if relevant
6. Include a task for identifying gaps and what CANNOT be verified

Return a JSON array of task descriptions:
[
  {"order": 1, "description": "Identify and verify the primary actors involved..."},
  {"order": 2, "description": "Verify the specific method/mechanism described..."},
  {"order": 3, "description": "Find official documents and primary sources..."},
  {"order": 4, "description": "Search for counter-narratives and opposing perspectives..."},
  {"order": 5, "description": "Assess financial/market/geopolitical impact..."},
  {"order": 6, "description": "Identify what is NOT verifiable in public sources..."}
]
"""


def _decompose_query(query: str) -> list[dict]:
    """Use LLM to decompose Wilson's query into investigation tasks."""
    client = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key=OLLAMA_API_KEY)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user_msg = f"""Decompose this investigation request into specific OSINT research tasks.

REQUEST: {query}
TODAY'S DATE: {today}

Return ONLY a JSON array of tasks. No other text."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        text = response.choices[0].message.content or "[]"

        # Parse JSON array
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        logger.error("Director decomposition failed: %s", e)

    # Fallback: single generic task
    return [
        {"order": 1, "description": f"Research and verify all claims about: {query}"},
        {"order": 2, "description": f"Find counter-narratives and opposing perspectives on: {query}"},
        {"order": 3, "description": f"Identify financial, political, and geopolitical impact of: {query}"},
    ]


def _update_status(supabase, investigation_id: str, status: str, extra: dict | None = None):
    """Update investigation status in Supabase."""
    update = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        update.update(extra)
    if status == "completed":
        update["completed_at"] = datetime.now(timezone.utc).isoformat()
    supabase.table("elite_investigations").update(update).eq("id", investigation_id).execute()


def _log_activity(supabase, investigation_id: str, action: str, details: dict | None = None):
    """Log activity to audit trail."""
    try:
        supabase.table("elite_activity_log").insert({
            "investigation_id": investigation_id,
            "agent": "director",
            "action": action,
            "details": details or {},
        }).execute()
    except Exception as e:
        logger.warning("Failed to log activity: %s", e)


async def run_investigation(query: str, wilson_chat_id: int, send_update) -> dict:
    """
    Run a full investigation pipeline.

    Args:
        query: Wilson's investigation request
        wilson_chat_id: Telegram chat ID for updates
        send_update: async callable(chat_id, text) to send Telegram messages

    Returns:
        dict with investigation results
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    started_at = datetime.now(timezone.utc)

    # ── Phase 0: Create investigation ────────────────────────────────
    await send_update(wilson_chat_id,
        "🔍 *Investigação iniciada.*\nA decompor o pedido em tarefas de pesquisa...")

    tasks = _decompose_query(query)
    task_descriptions = [t.get("description", "") for t in tasks]

    inv_result = supabase.table("elite_investigations").insert({
        "wilson_query": query,
        "investigation_plan": tasks,
        "status": "pending",
        "director_model": MODEL,
        "wilson_chat_id": wilson_chat_id,
    }).execute()

    investigation_id = inv_result.data[0]["id"]
    _log_activity(supabase, investigation_id, "investigation_created", {
        "query": query[:500], "tasks_count": len(tasks),
    })

    # Create tasks in Supabase
    for task in tasks:
        supabase.table("elite_tasks").insert({
            "investigation_id": investigation_id,
            "task_order": task.get("order", 0),
            "description": task.get("description", ""),
            "status": "pending",
        }).execute()

    task_list = "\n".join(f"  {i+1}. {d[:80]}" for i, d in enumerate(task_descriptions))
    await send_update(wilson_chat_id,
        f"📋 *Plano de investigação* ({len(tasks)} tarefas):\n{task_list}\n\n"
        f"🔎 Reporter em acção...")

    # ── Phase 1: Reporter (OSINT Research) ───────────────────────────
    _update_status(supabase, investigation_id, "researching")
    _log_activity(supabase, investigation_id, "reporter_started")

    try:
        findings_count = await asyncio.to_thread(run_elite_reporter, investigation_id)
    except Exception as e:
        logger.error("Reporter failed: %s", e)
        findings_count = 0
        _update_status(supabase, investigation_id, "failed")
        await send_update(wilson_chat_id, f"❌ Reporter falhou: {str(e)[:200]}")
        return {"status": "failed", "error": str(e)}

    _log_activity(supabase, investigation_id, "reporter_completed", {
        "findings_count": findings_count,
    })

    await send_update(wilson_chat_id,
        f"📋 *Recolha concluída:* {findings_count} factos encontrados.\n"
        f"🔬 FC Forense a verificar (verificação adversarial)...")

    # ── Phase 2: Fact-Checker Forense (Adversarial Verification) ─────
    _update_status(supabase, investigation_id, "verifying")
    _log_activity(supabase, investigation_id, "fact_checker_started")

    try:
        fc_stats = await asyncio.to_thread(run_elite_fact_checker, investigation_id)
    except Exception as e:
        logger.error("Fact-checker failed: %s", e)
        fc_stats = {"verified": 0, "disputed": 0, "rejected": 0, "needs_research": 0}

    _log_activity(supabase, investigation_id, "fact_checker_completed", fc_stats)

    v = fc_stats.get("verified", 0)
    r = fc_stats.get("rejected", 0)
    d = fc_stats.get("disputed", 0)
    await send_update(wilson_chat_id,
        f"✅ *Verificação concluída:*\n"
        f"  • {v} confirmados\n"
        f"  • {d} disputados\n"
        f"  • {r} rejeitados\n\n"
        f"✍️ Escritor Elite a redigir relatório...")

    # ── Phase 3: Writer (Report Generation) ──────────────────────────
    _update_status(supabase, investigation_id, "writing")
    _log_activity(supabase, investigation_id, "writer_started")

    try:
        report = await asyncio.to_thread(run_elite_writer, investigation_id)
    except Exception as e:
        logger.error("Writer failed: %s", e)
        report = None

    if not report:
        _update_status(supabase, investigation_id, "failed")
        await send_update(wilson_chat_id, "❌ Escritor falhou a gerar relatório.")
        return {"status": "failed", "error": "Writer failed"}

    # ── Phase 4: Delivery ────────────────────────────────────────────
    confidence = report.get("global_confidence", 0)
    if isinstance(confidence, (int, float)):
        conf_pct = f"{confidence:.0%}" if confidence <= 1 else f"{confidence}%"
    else:
        conf_pct = str(confidence)

    _update_status(supabase, investigation_id, "completed", {
        "global_confidence": confidence if isinstance(confidence, (int, float)) else 0,
    })
    _log_activity(supabase, investigation_id, "investigation_completed", {
        "report_id": report.get("report_id"),
        "global_confidence": confidence,
        "duration_seconds": (datetime.now(timezone.utc) - started_at).total_seconds(),
    })

    # Send summary to Wilson
    summary = report.get("summary", "Relatório gerado sem resumo.")
    title = report.get("title", "Relatório de Investigação")

    await send_update(wilson_chat_id,
        f"📰 *{title}*\n\n"
        f"{summary}\n\n"
        f"🎯 Confiança global: *{conf_pct}*\n"
        f"📊 Factos usados: {v} verificados | {r} rejeitados\n"
        f"⏱️ Tempo: {(datetime.now(timezone.utc) - started_at).total_seconds():.0f}s\n\n"
        f"_Relatório completo guardado. Usa /relatorio para ver._")

    # Send the full markdown report in a second message (if not too long)
    markdown = report.get("markdown", "")
    if markdown and len(markdown) < 4000:
        await send_update(wilson_chat_id, markdown)
    elif markdown:
        # Split into chunks for Telegram (4096 char limit)
        chunks = [markdown[i:i+4000] for i in range(0, len(markdown), 4000)]
        for chunk in chunks[:5]:  # Max 5 chunks
            await send_update(wilson_chat_id, chunk)

    return {
        "status": "completed",
        "investigation_id": investigation_id,
        "report": report,
        "stats": fc_stats,
    }
