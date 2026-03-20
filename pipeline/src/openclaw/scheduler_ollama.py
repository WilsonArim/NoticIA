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
    → [fact_checker]   cada 25 min  — web search + verificação factual (Nemotron 3 Super)
    → intake_queue (status='approved')
    → [escritor]       cada 30 min  — escrita PT-PT (Nemotron 3 Super)
    → articles (status='published')
    → [dossie]         cada 6h      — síntese temática, dossiês investigativos

Nota sobre triagem.py:
  A triagem está mantida no scheduler para processar items 'pending' que possam
  ter chegado de outras fontes. Nos eventos processados pelo dispatcher, a triagem
  é um no-op (o dispatcher insere directamente com status='auditor_approved').
  A triagem será deprecated quando todo o pipeline estiver migrado.
"""
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

load_dotenv()

from openclaw.agents.dispatcher import run_dispatcher
from openclaw.agents.triagem import run_triagem
from openclaw.agents.fact_checker import run_fact_checker
from openclaw.agents.escritor import run_escritor
# dossie.py DEPRECATED 2026-03-19 — substituído pela Equipa de Investigação Elite
# (reporter-investigacao + fc-forense + publisher-elite, aprovação humana de Wilson)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(job_defaults={"misfire_grace_time": 120})

# ── Camada 2 — Dispatcher LLM (substitui bridge.py + triagem para novos eventos) ──
# Cada 5 min: lê raw_events, raciocina semanticamente, faz routing para reporters
scheduler.add_job(
    run_dispatcher,
    IntervalTrigger(minutes=5),
    id="dispatcher",
    max_instances=1,
)

# ── Camada 3 (legado) — Triagem (no-op para eventos do dispatcher) ────────────────
# Mantida para processar items 'pending' que possam existir no queue.
# Dispatcher insere com 'auditor_approved', por isso a triagem não toca nesses items.
# TODO: deprecar quando todo o pipeline estiver migrado para o dispatcher.
scheduler.add_job(
    run_triagem,
    IntervalTrigger(minutes=20),
    id="triagem",
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
    logger.info("Modelo Dispatcher:    %s", "nvidia/nemotron-nano-30b-instruct:free")
    logger.info("Modelo Editorial:     %s", "nvidia/nemotron-3-super-120b-a12b:free")
    logger.info("=" * 60)

    # Arrancar agentes iniciais antes do scheduler (warm-up)
    logger.info("Warm-up: dispatcher (primeiro batch de raw_events)...")
    run_dispatcher()

    scheduler.start()
    logger.info("Scheduler activo. Jobs: dispatcher(5m) | triagem(20m, legado) | fact_checker(25m) | escritor(30m)")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Encerrando scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler encerrado.")
