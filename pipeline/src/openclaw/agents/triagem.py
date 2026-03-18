"""
Agente de Triagem — DeepSeek V3.2
Classifica items da intake_queue por área, valida frescura, atribui score.
Lê status='pending', escreve status='auditor_approved' ou 'auditor_failed'.
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta

from supabase import create_client

from openclaw.agents.ollama_client import chat

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_TRIAGEM", "deepseek-v3.2:cloud")
BATCH_SIZE = int(os.getenv("TRIAGEM_BATCH_SIZE", "25"))

# Máximo de dias desde o evento real (não a data de coleta)
MAX_EVENT_AGE_DAYS = int(os.getenv("MAX_EVENT_AGE_DAYS", "7"))

AREAS_VALIDAS = [
    "portugal", "europa", "mundo", "economia", "tecnologia",
    "ciencia", "saude", "cultura", "desporto", "geopolitica",
    "defesa", "clima", "sociedade", "justica", "educacao",
]


def run_triagem():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("intake_queue")
        .select("*")
        .eq("status", "pending")
        .order("score", desc=True)
        .limit(BATCH_SIZE)
        .execute()
    )

    items = result.data or []
    if not items:
        logger.info("Triagem: sem items pendentes")
        return

    logger.info("Triagem: processando %d items com %s", len(items), MODEL)

    for item in items:
        try:
            result_json = _classify_item(item)

            # ── Check determinístico de frescura ────────────────────────
            # O LLM extrai a data real do evento; o Python decide se é stale.
            data_real_str = result_json.get("data_real_evento", "")
            stale, motivo_stale = _is_stale(data_real_str, item)

            if stale:
                supabase.table("intake_queue").update({
                    "status": "auditor_failed",
                    "error_message": motivo_stale,
                }).eq("id", item["id"]).execute()
                logger.info("Triagem: STALE rejeitado — '%s' (%s)", item.get("title", "")[:60], motivo_stale)

            elif result_json.get("rejeitar"):
                supabase.table("intake_queue").update({
                    "status": "auditor_failed",
                    "error_message": result_json.get("notas", "Rejeitado pela triagem"),
                }).eq("id", item["id"]).execute()
            else:
                supabase.table("intake_queue").update({
                    "status": "auditor_approved",
                    "area": result_json.get("area", item.get("area", "mundo")),
                    "score": result_json.get("score", item.get("score", 0.5)),
                    "metadata": {
                        **(item.get("metadata") or {}),
                        "triagem_notes": result_json.get("notas", ""),
                        "data_real_evento": data_real_str,
                    },
                }).eq("id", item["id"]).execute()

        except Exception as e:
            logger.error("Triagem erro item %s: %s", item["id"], e)


def _is_stale(data_real_str: str, item: dict) -> tuple[bool, str]:
    """Verifica deterministicamente se o evento é demasiado antigo.

    Prioridade:
    1. data_real_evento extraída pelo LLM (data do evento, não da coleta)
    2. received_at como fallback (data de coleta — menos fiável)
    """
    hoje = datetime.now(timezone.utc).date()
    cutoff = hoje - timedelta(days=MAX_EVENT_AGE_DAYS)

    # 1. Tentar com a data real extraída pelo LLM
    if data_real_str and len(data_real_str) >= 10:
        try:
            evento_date = datetime.strptime(data_real_str[:10], "%Y-%m-%d").date()
            if evento_date < cutoff:
                return True, f"stale_event: evento de {data_real_str} (>{MAX_EVENT_AGE_DAYS} dias)"
            return False, ""
        except ValueError:
            pass

    # 2. Fallback: received_at (data de coleta)
    received_at = item.get("received_at", "")
    if received_at:
        try:
            dt = datetime.fromisoformat(str(received_at).replace("Z", "+00:00"))
            if dt.date() < cutoff:
                return True, f"stale_received: colectado em {dt.date()} (>{MAX_EVENT_AGE_DAYS} dias)"
        except ValueError:
            pass

    return False, ""


def _classify_item(item: dict) -> dict:
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""És um editor de triagem de notícias. Analisa este item e classifica-o.

HOJE: {hoje}

TÍTULO: {item.get("title", "")}
FONTE: {item.get("url", "")}
RESUMO: {item.get("content", "")[:500]}
DATA DE COLETA (quando o sistema recolheu — NÃO é necessariamente a data do evento): {item.get("received_at", "desconhecida")}

INSTRUÇÕES:
1. Determina a data REAL em que o evento aconteceu (não quando foi publicado nem coletado).
   - Se não conseguires determinar a data real, usa a data de coleta como estimativa.
   - Formato obrigatório: AAAA-MM-DD
2. Qual é a área correcta? Escolhe UMA: {", ".join(AREAS_VALIDAS)}
3. Qual é o score de relevância (0.0 a 1.0) para um leitor português?
4. Deves rejeitar se: conteúdo spam/publicidade, duplicado óbvio, sem interesse jornalístico.
   (A validação de frescura da data é feita automaticamente pelo sistema — não precisa de rejeitar por data aqui.)

Responde APENAS em JSON válido:
{{
  "rejeitar": false,
  "data_real_evento": "AAAA-MM-DD",
  "area": "geopolitica",
  "score": 0.75,
  "notas": "observação breve"
}}"""

    response = chat(MODEL, [{"role": "user", "content": prompt}], temperature=0.1)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    return {"rejeitar": False, "area": "mundo", "score": 0.5, "data_real_evento": ""}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_triagem()
