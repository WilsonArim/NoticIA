"""
Dispatcher LLM — Classificação Semântica de raw_events

Substitui bridge.py (keyword scoring) + triagem.py (classificação básica).
Usa Nemotron Nano 30B via OpenRouter para raciocinar semanticamente sobre
cada evento e fazer routing para o reporter especialista correcto.

Fluxo:
  raw_events (processed=false)
    → LLM raciocina sobre título + conteúdo + fonte
    → categorias (1-N das 19 activas), relevância PT, prioridade, frescura
    → intake_queue (status='auditor_approved') — uma row por categoria
    → mark raw_events.processed = true

Notas:
  - Não usa keywords. Raciocina sobre o conteúdo completo.
  - Eventos multi-temáticos geram múltiplas rows na intake_queue.
  - Insere com status='auditor_approved' (bypass da triagem, que fica no-op).
  - Frescura verificada deterministicamente (não pelo LLM).

Frequência: cada 5 min via scheduler_ollama.py
Batch:      20 eventos por run (DISPATCHER_BATCH_SIZE)
Modelo:     MODEL_DISPATCHER (fallback: MODEL_TRIAGEM → Nano 30B)
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta

from supabase import create_client

from openclaw.agents.ollama_client import chat

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# MODEL_DISPATCHER pode ser sobreposto no .env — usa MODEL_TRIAGEM como fallback
# (ambos devem apontar para Nano 30B via OpenRouter na config actual)
MODEL = os.getenv(
    "MODEL_DISPATCHER",
    os.getenv("MODEL_TRIAGEM", "nvidia/nemotron-nano-30b-instruct:free"),
)

BATCH_SIZE = int(os.getenv("DISPATCHER_BATCH_SIZE", "20"))
MAX_EVENT_AGE_DAYS = int(os.getenv("MAX_EVENT_AGE_DAYS", "7"))

# Categorias válidas — devem corresponder a reporter_configs.area no Supabase
CATEGORIAS_VALIDAS: set[str] = {
    "geopolitica", "politica_intl", "diplomacia", "defesa", "defesa_estrategica",
    "tecnologia", "ciencia", "energia", "clima",
    "portugal", "sociedade",
    "economia", "financas", "crypto", "regulacao",
    "saude", "direitos_humanos",
    "desinformacao", "crime_organizado",
}

# Áreas desactivadas editorialmente — eventos destas áreas são rejeitados
DISABLED_AREAS: set[str] = {"desporto", "sports", "sport"}

# ── System prompt ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """És o Dispatcher do Curador de Noticias. Recebes artigos em bruto dos coletores.
A tua missão é analisar cada artigo semanticamente e decidir para que reporter especialista o enviar.
Não usas keywords — raciocinas sobre o conteúdo completo.

Para cada artigo, raciocina em sequência:

1. TEMA REAL: De que é que este artigo trata realmente? Ignora títulos sensacionalistas — analisa o conteúdo.

2. CATEGORIA: Qual das 19 categorias activas melhor descreve este artigo?
   Categorias disponíveis: geopolitica, politica_intl, diplomacia, defesa, defesa_estrategica,
   tecnologia, ciencia, energia, clima, portugal, sociedade, economia, financas, crypto,
   regulacao, saude, direitos_humanos, desinformacao, crime_organizado

3. MULTI-TEMÁTICO: Este artigo pertence genuinamente a mais de uma categoria?
   Exemplo: "BCE sobe taxas por receio de recessão após guerra comercial EUA-China"
   → economia + geopolitica (sim, as duas fazem sentido)
   Não abuses — só inclui categorias adicionais se forem claramente relevantes.

4. RELEVÂNCIA PORTUGAL (0.0-1.0):
   1.0 = afecta directamente Portugal (política PT, economia PT, desastres em PT)
   0.7 = afecta Portugal via UE/NATO/CPLP ou mercados europeus
   0.5 = impacto global que Portugal sente indirectamente
   0.2 = relevante para leitor informado mas sem impacto directo em PT
   0.0 = sem qualquer relevância para Portugal

5. PRIORIDADE PRELIMINAR:
   P1 = breaking news urgente (conflito armado activo, crash mercados, crise política imediata)
   P2 = notícia importante do dia (decisão política relevante, resultado económico, evento significativo)
   P3 = análise, contexto, tendência (relatório, estudo, desenvolvimento gradual)

6. REJEITAR? Rejeita se:
   - Desporto local de outro país sem impacto em PT
   - Fait-divers, entretenimento, celebridades sem impacto real
   - Spam, publicidade, conteúdo sem valor noticioso
   - Completamente irrelevante para Portugal (relevancia_pt < 0.1)

7. DATA REAL DO EVENTO (YYYY-MM-DD):
   Determina quando o evento realmente aconteceu, não quando foi publicado ou coletado.
   Se não conseguires determinar, devolve null.

Responde APENAS com JSON válido, sem texto adicional antes ou depois:
{
  "categories": ["categoria_principal"],
  "relevancia_pt": 0.0,
  "priority": "P1|P2|P3",
  "reject": false,
  "reject_reason": null,
  "data_real_evento": "YYYY-MM-DD ou null",
  "reasoning": "raciocínio conciso (1-2 frases) em PT-PT"
}"""


# ── Main function ────────────────────────────────────────────────────────

def run_dispatcher() -> dict[str, int]:
    """Processa raw_events não processados e insere na intake_queue.

    Retorna stats: {fetched, queued, rejected, stale, errors}
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    stats = {"fetched": 0, "queued": 0, "rejected": 0, "stale": 0, "errors": 0}

    # --- pipeline_runs logging: início ---
    run_id = None
    try:
        run_row = supabase.table("pipeline_runs").insert({
            "stage": "dispatcher",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events_in": 0,
            "events_out": 0,
        }).execute()
        run_id = run_row.data[0]["id"] if run_row.data else None
    except Exception as e:
        logger.warning("Dispatcher: falha ao criar pipeline_run: %s", e)

    # 1. Buscar raw_events por processar
    result = (
        supabase.table("raw_events")
        .select("id, title, content, url, source_collector, published_at, created_at, raw_metadata")
        .eq("processed", False)
        .order("published_at", desc=True)
        .limit(BATCH_SIZE)
        .execute()
    )

    events = result.data or []
    if not events:
        logger.info("Dispatcher: sem raw_events por processar")
        return stats

    stats["fetched"] = len(events)
    logger.info("Dispatcher: processando %d eventos com %s", len(events), MODEL)

    event_ids_to_mark: list[str] = []
    intake_rows: list[dict] = []

    for event in events:
        event_id: str = event["id"]
        try:
            # 2. Verificação de frescura antes do LLM (economia de tokens)
            collected_at = event.get("published_at") or event.get("created_at", "")
            stale, stale_reason = _is_stale_from_collection_date(collected_at)
            if stale:
                logger.info("Dispatcher: STALE (pré-LLM) '%s' — %s",
                            event.get("title", "")[:60], stale_reason)
                stats["stale"] += 1
                event_ids_to_mark.append(event_id)
                continue

            # 3. Classificação LLM
            classification = _classify_event(event)

            # 4. Verificação de frescura com data extraída pelo LLM
            data_real = classification.get("data_real_evento")
            if data_real:
                stale, stale_reason = _is_stale_by_date(data_real)
                if stale:
                    logger.info("Dispatcher: STALE (pós-LLM) '%s' — %s",
                                event.get("title", "")[:60], stale_reason)
                    stats["stale"] += 1
                    event_ids_to_mark.append(event_id)
                    continue

            # 5. Rejeição editorial
            if classification.get("reject"):
                logger.info("Dispatcher: REJEITADO '%s' — %s",
                            event.get("title", "")[:60],
                            classification.get("reject_reason", "sem motivo"))
                stats["rejected"] += 1
                event_ids_to_mark.append(event_id)
                continue

            # 6. Validar categorias
            raw_categories: list[str] = classification.get("categories", [])
            valid_categories = [c for c in raw_categories if c in CATEGORIAS_VALIDAS]

            if not valid_categories:
                logger.warning("Dispatcher: nenhuma categoria válida para '%s' (recebeu: %s)",
                               event.get("title", "")[:60], raw_categories)
                # Fallback para "mundo" se o LLM devolveu algo inválido
                valid_categories = ["geopolitica"]

            # Filtrar categorias desactivadas
            valid_categories = [c for c in valid_categories if c.lower() not in DISABLED_AREAS]
            if not valid_categories:
                logger.info("Dispatcher: REJEITADO (área desactivada) '%s'",
                            event.get("title", "")[:60])
                stats["rejected"] += 1
                event_ids_to_mark.append(event_id)
                continue

            # 7. Construir rows para intake_queue (uma por categoria)
            relevancia_pt = float(classification.get("relevancia_pt", 0.5))
            priority = classification.get("priority", "p3").lower()
            reasoning = classification.get("reasoning", "")

            for category in valid_categories:
                intake_rows.append({
                    "source_event_id": event_id,
                    "title": event.get("title", ""),
                    "content": (event.get("content") or "")[:5000],
                    "url": event.get("url", ""),
                    "area": category,
                    "score": round(relevancia_pt, 4),
                    "priority": priority,
                    "status": "auditor_approved",  # dispatcher já fez análise LLM
                    "language": "pt",
                    "metadata": {
                        "source_collector": event.get("source_collector", ""),
                        "dispatcher_reasoning": reasoning,
                        "data_real_evento": data_real or "",
                        "all_categories": valid_categories,
                        "dispatcher_version": "v1-llm",
                        "model": MODEL,
                    },
                })

            event_ids_to_mark.append(event_id)
            stats["queued"] += len(valid_categories)

            logger.info(
                "Dispatcher: '%s' → %s | prioridade=%s | pt=%.2f",
                event.get("title", "")[:60],
                valid_categories,
                priority.upper(),
                relevancia_pt,
            )

        except Exception as e:
            logger.error("Dispatcher: erro no evento %s: %s", event_id, e)
            stats["errors"] += 1
            # Marcar como processed para evitar loop infinito em eventos problemáticos
            event_ids_to_mark.append(event_id)

    # 8. Inserir na intake_queue em batch
    if intake_rows:
        try:
            supabase.table("intake_queue").insert(intake_rows).execute()
            logger.info("Dispatcher: %d rows inseridas na intake_queue", len(intake_rows))
        except Exception as e:
            logger.error("Dispatcher: falha ao inserir intake_queue: %s", e)
            stats["errors"] += 1

    # 9. Marcar raw_events como processed
    if event_ids_to_mark:
        try:
            # Supabase Python SDK não suporta .in_() directamente no update — usar chunks
            for chunk in _chunks(event_ids_to_mark, 50):
                supabase.table("raw_events").update({"processed": True}).in_(
                    "id", chunk
                ).execute()
            logger.info("Dispatcher: %d raw_events marcados como processed",
                        len(event_ids_to_mark))
        except Exception as e:
            logger.error("Dispatcher: falha ao marcar processed: %s", e)
            stats["errors"] += 1

    logger.info(
        "Dispatcher concluído: fetched=%d queued=%d rejected=%d stale=%d errors=%d",
        stats["fetched"], stats["queued"], stats["rejected"], stats["stale"], stats["errors"],
    )

    # --- pipeline_runs logging: fim ---
    if run_id:
        try:
            final_status = "completed" if stats["errors"] == 0 else "completed_with_errors"
            supabase.table("pipeline_runs").update({
                "status": final_status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "events_in": stats["fetched"],
                "events_out": stats["queued"],
                "metadata": stats,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Dispatcher: falha ao actualizar pipeline_run: %s", e)

    return stats


# ── LLM call ─────────────────────────────────────────────────────────────

def _classify_event(event: dict) -> dict:
    """Chama o LLM para classificar um raw_event. Devolve dict com a classificação."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    user_prompt = (
        f"Hoje: {hoje}\n\n"
        f"TÍTULO: {event.get('title', '(sem título)')}\n"
        f"FONTE/URL: {event.get('url', '')}\n"
        f"COLETOR: {event.get('source_collector', '')}\n"
        f"DATA DE COLETA: {event.get('published_at') or event.get('created_at', 'desconhecida')}\n"
        f"CONTEÚDO:\n{(event.get('content') or '')[:800]}\n\n"
        "Classifica este evento. Raciocina sobre o conteúdo real."
    )

    response = chat(
        MODEL,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=512,
    )

    # Extrair JSON da resposta (o modelo pode envolver o JSON em ```json ... ```)
    return _parse_json_response(response, event.get("title", ""))


def _parse_json_response(response: str, title: str) -> dict:
    """Extrai e parseia o JSON da resposta do LLM com fallback robusto."""
    # Tentar extrair de bloco ```json
    if "```" in response:
        start = response.find("```")
        end = response.rfind("```")
        if start != end:
            inner = response[start + 3:end].strip()
            if inner.startswith("json"):
                inner = inner[4:].strip()
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                pass

    # Tentar extrair JSON directo
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

    logger.warning(
        "Dispatcher: falha a parsear JSON para '%s' — resposta: %s",
        title[:60],
        response[:300],
    )
    # Fallback: rejeitar para não bloquear o pipeline
    return {
        "categories": [],
        "relevancia_pt": 0.0,
        "priority": "p3",
        "reject": True,
        "reject_reason": "dispatcher_parse_error",
        "data_real_evento": None,
        "reasoning": "Falha a parsear resposta do LLM",
    }


# ── Freshness checks ─────────────────────────────────────────────────────

def _is_stale_by_date(data_real_str: str) -> tuple[bool, str]:
    """Verifica se a data real do evento está fora do MAX_EVENT_AGE_DAYS."""
    if not data_real_str or len(str(data_real_str)) < 10:
        return False, ""
    try:
        evento_date = datetime.strptime(str(data_real_str)[:10], "%Y-%m-%d").date()
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=MAX_EVENT_AGE_DAYS)
        if evento_date < cutoff:
            return True, f"stale_event: evento de {data_real_str} (>{MAX_EVENT_AGE_DAYS} dias)"
    except ValueError:
        pass
    return False, ""


def _is_stale_from_collection_date(collected_at: str) -> tuple[bool, str]:
    """Verificação rápida de frescura pela data de coleta — evita chamar o LLM
    em eventos obviamente antigos (>3× o limite). A data real pode ser mais recente,
    por isso usamos um factor multiplicador para não rejeitar prematuramente."""
    if not collected_at:
        return False, ""
    try:
        dt = datetime.fromisoformat(str(collected_at).replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_EVENT_AGE_DAYS * 3)
        if dt < cutoff:
            return True, f"stale_collected: coletado em {dt.date()} (muito antigo)"
    except ValueError:
        pass
    return False, ""


# ── Utilities ─────────────────────────────────────────────────────────────

def _chunks(lst: list, n: int):
    """Divide uma lista em chunks de tamanho n."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    result = run_dispatcher()
    print(f"\nResultado: {result}")
