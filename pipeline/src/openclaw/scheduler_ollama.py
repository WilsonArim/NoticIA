"""
Scheduler principal — Ollama Cloud
Corre os 4 agentes Ollama nos intervalos correctos.
Arranca também o bot Telegram para edição manual (se TELEGRAM_BOT_TOKEN estiver configurado).

Uso:
  cd pipeline && source .venv/bin/activate
  python -m openclaw.scheduler_ollama
"""
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

load_dotenv()

from openclaw.agents.triagem import run_triagem
from openclaw.agents.fact_checker import run_fact_checker
from openclaw.agents.dossie import run_dossie
from openclaw.agents.escritor import run_escritor
from openclaw.agents.telegram_editor import run_telegram_editor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# BackgroundScheduler para correr em paralelo com o bot Telegram
scheduler = BackgroundScheduler()

# pipeline-triagem: cada 20 min (DeepSeek V3.2)
scheduler.add_job(run_triagem, IntervalTrigger(minutes=20), id="triagem", max_instances=1)

# agente-fact-checker: cada 30 min (Nemotron 3 Super)
scheduler.add_job(run_fact_checker, IntervalTrigger(minutes=30), id="fact_checker", max_instances=1)

# agente-dossie: cada 6h (Nemotron 3 Super)
scheduler.add_job(run_dossie, IntervalTrigger(hours=6), id="dossie", max_instances=1)

# pipeline-escritor: cada 30 min (Qwen 3.5)
scheduler.add_job(run_escritor, IntervalTrigger(minutes=30), id="escritor", max_instances=1)


if __name__ == "__main__":
    logger.info("Iniciando scheduler Ollama — DeepSeek V3.2 + Nemotron 3 Super + Qwen 3.5")

    # Arrancar agentes iniciais numa thread separada para não bloquear o bot
    def _startup():
        run_dossie()
        run_triagem()

    threading.Thread(target=_startup, daemon=True).start()

    scheduler.start()
    logger.info("Scheduler activo. A arrancar bot Telegram...")

    # Bot Telegram corre no thread principal (blocking)
    telegram_app = run_telegram_editor()
    if telegram_app:
        telegram_app.run_polling(drop_pending_updates=True)
    else:
        # Sem Telegram — manter processo vivo com o scheduler
        logger.info("Bot Telegram não configurado — scheduler a correr sem bot.")
        import time
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
