"""
Agente de Triagem — DeepSeek V3.2
Classifica items da intake_queue por área, valida frescura, atribui score.
Lê status='pending', escreve status='auditor_approved' ou 'auditor_failed'.
"""
import os
import json
import logging
from datetime import datetime, timezone

from supabase import create_client

from openclaw.agents.ollama_client import chat

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
MODEL = os.getenv("MODEL_TRIAGEM", "deepseek-v3.2:cloud")
BATCH_SIZE = int(os.getenv("TRIAGEM_BATCH_SIZE", "25"))

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

            if result_json.get("rejeitar"):
                supabase.table("intake_queue").update({
                    "status": "auditor_failed",
                    "error_message": result_json.get("motivo", "Rejeitado pela triagem"),
                }).eq("id", item["id"]).execute()
            else:
                supabase.table("intake_queue").update({
                    "status": "auditor_approved",
                    "area": result_json.get("area", item.get("area", "mundo")),
                    "score": result_json.get("score", item.get("score", 0.5)),
                    "metadata": {
                        **(item.get("metadata") or {}),
                        "triagem_notes": result_json.get("notas", ""),
                    },
                }).eq("id", item["id"]).execute()

        except Exception as e:
            logger.error("Triagem erro item %s: %s", item["id"], e)


def _classify_item(item: dict) -> dict:
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""És um editor de triagem de notícias. Analisa este item e classifica-o.

HOJE: {hoje}

TÍTULO: {item.get("title", "")}
FONTE: {item.get("url", "")}
RESUMO: {item.get("content", "")[:500]}
DATA DO ITEM: {item.get("received_at", "desconhecida")}

INSTRUÇÕES:
1. A notícia é recente (menos de 72h)? Se for mais antiga, rejeita.
2. Qual é a área correcta? Escolhe UMA: {", ".join(AREAS_VALIDAS)}
3. Qual é o score de relevância (0.0 a 1.0) para um leitor português?
4. Deves rejeitar se: notícia velha, duplicado óbvio, conteúdo spam/publicidade.

Responde APENAS em JSON válido:
{{
  "rejeitar": false,
  "area": "geopolitica",
  "score": 0.75,
  "notas": "motivo breve se rejeitar, ou observação relevante"
}}"""

    response = chat(MODEL, [{"role": "user", "content": prompt}], temperature=0.1)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])

    return {"rejeitar": False, "area": "mundo", "score": 0.5}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_triagem()
