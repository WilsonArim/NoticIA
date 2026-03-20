"""
Scheduler principal — OpenClaw Pipeline (Oracle VM)
Corre todos os agentes LLM nos intervalos correctos.

Uso:
  cd pipeline && source .venv/bin/activate
  python -m openclaw.scheduler_ollama

Fluxo do pipeline:
  raw_events
    → [dispatcher]     cada 5 min   — classificação semântica LLM, routing para reporters
    → intake_queue (status='auditor_approved')
    → [fact_checker]   cada 25 min  — web search + verificação factual
    → intake_queue (status='approved')
    → [escritor]       cada 30 min  — escrita PT-PT
    → articles (status='published')

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
from dotenv import load_dotenv

load_dotenv()

from openclaw.agents.dispatcher import run_dispatcher
# triagem.py DEPRECATED 2026-03-20 — pipeline totalmente migrado para dispatcher LLM.
# O dispatcher insere directamente com status='auditor_approved', tornando a triagem
# um no-op. intake_queue limpa. Triagem removida do scheduler.
from openclaw.agents.fact_checker import run_fact_checker
from openclaw.agents.escritor import run_escritor
# dossie.py DEPRECATED 2026-03-19 — substituído pela Equipa de Investigação Elite
# (reporter-investigacao + fc-forense + publisher-elite, aprovação humana de Wilson)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def sync_models_to_supabase() -> None:
    """Propaga os modelos do .env para adapter_config.model no Supabase.

    O .env é a única fonte de verdade. Esta função garante que o Paperclip UI
    reflecte sempre os modelos activos, sem intervenção manual.

    Mapeamento role → variável de ambiente:
      dispatcher   → MODEL_DISPATCHER   (gpt-oss:20b   — routing rápido)
      reporter     → MODEL_REPORTER     (mistral-large-3:675b — PT-PT explícito)
      fact_checker → MODEL_FACTCHECKER  (kimi-k2-thinking — verificação agentica)
      auditor      → MODEL_AUDITOR      (cogito-2.1:671b — raciocínio crítico)
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
        "fact_checker": os.getenv("MODEL_FACTCHECKER",  "kimi-k2-thinking"),
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

# ── Camada 2 — Dispatcher LLM (substitui bridge.py + triagem para novos eventos) ──
# Cada 5 min: lê raw_events, raciocina semanticamente, faz routing para reporters
scheduler.add_job(
    run_dispatcher,
    IntervalTrigger(minutes=5),
    id="dispatcher",
    max_instances=1,
)

# ── Camada 3 — Fact-Checker (Nemotron 3 Super + web search) ──────────────────────
# Cada 25 min: lê 'auditor_approved', verifica factos com pesquisa real
scheduler.add_job(
    run_fact_checker,
    IntervalTrigger(minutes=25),
    id="fact_checker",
    max_instances=1,
)

# ── Camada 4 — Escritor (Nemotron 3 Super) ───────────────────────────────────────
# Cada 30 min: lê 'approved', escreve artigo em PT-PT, publica
scheduler.add_job(
    run_escritor,
    IntervalTrigger(minutes=30),
    id="escritor",
    max_instances=1,
)

# ── Dossiê — DEPRECATED 2026-03-19 ──────────────────────────────────────────────
# Substituído pela Equipa de Investigação Elite (reporter-investigacao + fc-forense
# + publisher-elite). A equipa elite raciocina profundamente, usa WebSearch forense
# + Crawl4AI, e requer aprovação de Wilson antes de publicar.
# NÃO reactivar. O agente dossie no Supabase está paused.


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OpenClaw Pipeline — Iniciando (Oracle VM)")
    logger.info("Modelo Dispatcher:    %s", os.getenv("MODEL_DISPATCHER", "n/a"))
    logger.info("Modelo Editorial:     %s", os.getenv("MODEL_FACTCHECKER", "n/a"))
    logger.info("=" * 60)

    # Sincronizar modelos do .env → Supabase (fonte de verdade única)
    logger.info("Sincronizando modelos .env → Supabase...")
    sync_models_to_supabase()

    # Arrancar agentes iniciais antes do scheduler (warm-up)
    logger.info("Warm-up: dispatcher (primeiro batch de raw_events)...")
    run_dispatcher()

    scheduler.start()
    logger.info("Scheduler activo. Jobs: dispatcher(5m) | fact_checker(25m) | escritor(30m)")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Encerrando scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler encerrado.")
