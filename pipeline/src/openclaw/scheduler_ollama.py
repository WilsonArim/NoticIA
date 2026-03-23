"""
Scheduler principal — OpenClaw Pipeline V2 (Oracle VM)
Corre todos os agentes LLM nos intervalos correctos.

Uso:
  cd pipeline && source venv/bin/activate
  python -m openclaw.scheduler_ollama

Fluxo do pipeline V2 (optimizado):
  raw_events
    → [dispatcher V2]  cada 5 min   — dedup + filtro + batch LLM + quality gate
    → intake_queue (status='auditor_approved')
    → [fact_checker]   cada 25 min  — web search + verificação factual
    → intake_queue (status='approved')
    → [escritor]       cada 30 min  — escrita PT-PT
    → articles (status='published')
    → [cronistas]      dom 10:00    — 10 crónicas semanais

Optimizações V2 vs V1:
  - Dedup pré-LLM: ~7% chamadas eliminadas
  - Filtro determinístico: ~60-70% chamadas eliminadas
  - Batching: 10 eventos por chamada LLM (~78% menos tokens)
  - Quality gate no dispatcher: elimina stage auditor separado

Fonte de verdade dos modelos: .env
  O .env é a única fonte de verdade. No arranque, sync_models_to_supabase()
  propaga automaticamente os modelos para o Supabase (adapter_config.model),
  mantendo o Paperclip UI sempre em sync sem intervenção manual.
"""
import logging
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

# V2: dispatcher com dedup + filtro + batching + quality gate
from openclaw.agents.dispatcher import run_dispatcher
from openclaw.agents.fact_checker_parallel import run_fact_checkers_parallel
from openclaw.agents.escritor import run_escritor
from openclaw.agents.cronistas import run_cronistas
from openclaw.collector_runner import run_collectors
from openclaw.engenheiro_pipeline import run_pipeline_health

from openclaw.logging_config import setup_logging  # noqa: E402

setup_logging()
logger = logging.getLogger(__name__)


def sync_models_to_supabase() -> None:
    """Propaga os modelos do .env para adapter_config.model no Supabase.

    O .env é a única fonte de verdade. Esta função garante que o Paperclip UI
    reflecte sempre os modelos activos, sem intervenção manual.

    Mapeamento role → variável de ambiente:
      dispatcher   → MODEL_DISPATCHER   (gpt-oss:20b   — routing rápido)
      reporter     → MODEL_REPORTER     (mistral-large-3:675b — PT-PT explícito)
      fact_checker → MODEL_FACTCHECKER  (deepseek-v3.2 — verificação profunda)
      auditor      → MODEL_AUDITOR      (cogito-2.1:671b — DEPRECATED: colapsado no dispatcher V2)
      writer       → MODEL_ESCRITOR     (mistral-large-3:675b — escrita PT-PT)
      editor       → MODEL_EDITOR_CHEFE (cogito-2.1:671b — julgamento editorial)
      columnist    → MODEL_CRONISTAS    (gemma3:27b — escrita criativa/expressiva)
      ceo          → MODEL_EDITOR_CHEFE (cogito-2.1:671b — decisão estratégica)
      engineer     → MODEL_ENGINEER     (devstral-2:123b — código)
      hr           → MODEL_EDITOR_CHEFE (cogito-2.1:671b — gestão)
      publisher    → MODEL_DISPATCHER   (gpt-oss:20b — leve, sem raciocínio editorial)
      collector    → (sem LLM, ignorado)
    """
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not supabase_key:
        logger.warning("sync_models: SUPABASE_URL ou SUPABASE_SERVICE_KEY em falta — a saltar sync")
        return

    role_to_model: dict[str, str | None] = {
        "dispatcher":   os.getenv("MODEL_DISPATCHER",   "gpt-oss:20b"),
        "reporter":     os.getenv("MODEL_REPORTER",     "mistral-large-3:675b"),
        "fact_checker": os.getenv("MODEL_FACTCHECKER",  "deepseek-v3.2"),
        "auditor":      os.getenv("MODEL_AUDITOR",      "cogito-2.1:671b"),
        "writer":       os.getenv("MODEL_ESCRITOR",     "mistral-large-3:675b"),
        "editor":       os.getenv("MODEL_EDITOR_CHEFE", "cogito-2.1:671b"),
        "columnist":    os.getenv("MODEL_CRONISTAS",    "gemma3:27b"),
        "ceo":          os.getenv("MODEL_EDITOR_CHEFE", "cogito-2.1:671b"),
        "engineer":     os.getenv("MODEL_ENGINEER",     "devstral-2:123b"),
        "hr":           os.getenv("MODEL_EDITOR_CHEFE", "cogito-2.1:671b"),
        "publisher":    os.getenv("MODEL_DISPATCHER",   "gpt-oss:20b"),
        "collector":    None,  # sem LLM
    }

    try:
        from supabase import create_client
        sb = create_client(supabase_url, supabase_key)
        agents = sb.table("agents").select("id,name,role,adapter_config").execute()
        updated = 0
        for a in agents.data:
            role = a.get("role", "")
            model = role_to_model.get(role)
            if model is None:
                continue
            cfg = a.get("adapter_config") or {}
            if cfg.get("model") != model:
                cfg["model"] = model
                sb.table("agents").update({"adapter_config": cfg}).eq("id", a["id"]).execute()
                updated += 1
        logger.info("sync_models: %d/%d agentes sincronizados no Supabase", updated, len(agents.data))
    except Exception as exc:
        logger.warning("sync_models: erro ao sincronizar — %s", exc)

scheduler = BackgroundScheduler(job_defaults={"misfire_grace_time": 120})

# ── Camada 1 — Collectors (RSS + GDELT) ──────────────────────────────────
# Cada 15 min: recolhe de 23+ RSS feeds e GDELT API, insere em raw_events
scheduler.add_job(
    run_collectors,
    IntervalTrigger(minutes=15),
    id="collectors",
    max_instances=1,
)

# ── Camada 2 — Dispatcher V2 (dedup + filtro + batch LLM + quality gate) ──
# Cada 5 min: lê raw_events, filtra sem LLM, classifica em batch
scheduler.add_job(
    run_dispatcher,
    IntervalTrigger(minutes=5),
    id="dispatcher",
    max_instances=1,
)

# ── Camada 3 — Fact-Checker (deepseek-v3.2 + web search) ────────────────
# Cada 25 min: 6 FCs sectoriais em paralelo (ThreadPoolExecutor, max_workers=3)
scheduler.add_job(
    run_fact_checkers_parallel,
    IntervalTrigger(minutes=25),
    id="fact_checker",
    max_instances=1,
)

# ── Camada 4 — Escritor (mistral-large-3:675b) ──────────────────────────
# Cada 30 min: lê 'approved', escreve artigo em PT-PT, publica
scheduler.add_job(
    run_escritor,
    IntervalTrigger(minutes=30),
    id="escritor",
    max_instances=1,
)

# ── Camada 5 — Engenheiro de Pipeline (watchdog) ────────────────────────
# Cada 30 min: sonda todos os estágios, detecta anomalias, alerta
scheduler.add_job(
    run_pipeline_health,
    IntervalTrigger(minutes=30),
    id="pipeline_health",
    max_instances=1,
)

# ── Camada 6 — Cronistas (gemma3:27b) ───────────────────────────────────
# Semanal: domingos às 10:00 UTC — gera 10 crónicas semanais
scheduler.add_job(
    run_cronistas,
    CronTrigger(day_of_week="sun", hour=10, minute=0),
    id="cronistas",
    max_instances=1,
)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OpenClaw Pipeline V2 — Iniciando (Oracle VM)")
    logger.info("Modelo Dispatcher:    %s", os.getenv("MODEL_DISPATCHER", "n/a"))
    logger.info("Modelo Fact-Checker:  %s", os.getenv("MODEL_FACTCHECKER", "n/a"))
    logger.info("Modelo Escritor:      %s", os.getenv("MODEL_ESCRITOR", "n/a"))
    logger.info("Optimizações: dedup + filtro + batch(%s) + quality_gate",
                os.getenv("DISPATCHER_LLM_BATCH_SIZE", "10"))
    logger.info("=" * 60)

    # Sincronizar modelos do .env → Supabase (fonte de verdade única)
    logger.info("Sincronizando modelos .env → Supabase...")
    sync_models_to_supabase()

    # Arrancar agentes iniciais antes do scheduler (warm-up)
    logger.info("Warm-up: collectors (RSS + GDELT)...")
    run_collectors()
    logger.info("Warm-up: dispatcher V2 (primeiro batch de raw_events)...")
    run_dispatcher()

    scheduler.start()
    logger.info("Scheduler activo. Jobs: collectors(15m) | dispatcher(5m) | fact_checker(25m) | escritor(30m) | pipeline_health(30m) | cronistas(dom 10h)")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Encerrando scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler encerrado.")
