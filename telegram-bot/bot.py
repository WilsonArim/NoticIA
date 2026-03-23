"""
Diretor Elite V2 — Telegram Bot com Pipeline Real
===================================================
Interface conversacional entre Wilson e a Equipa Elite de Investigação.
V2: Orquestra agentes REAIS (Reporter, FC Forense, Escritor) em vez de simular.

Comandos:
  /investiga [tema]       — Inicia investigação com pipeline completo
  /injecta URL [contexto] — V3: Injecta URL na pipeline contra-media (editorial_injection)
  /status                 — Status da investigação em curso
  /relatorio              — Ver último relatório completo
  /arquivo                — Listar investigações anteriores
  [texto livre]           — Conversa com o Diretor (modo consultivo)
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI
from telethon import TelegramClient, events

load_dotenv()

import hashlib
import re
try:
    import httpx
except ImportError:
    httpx = None

# Add current dir to path for elite modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("diretor-elite-bot")

# ── Config ────────────────────────────────────────────────────────────────────
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL = os.getenv("MODEL_DIRETOR_ELITE", "mistral-large-3:675b")
WILSON_ID = int(os.getenv("TELEGRAM_WILSON_CHAT_ID", "0"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ── Conversational mode system prompt ─────────────────────────────────────────
CONVERSATIONAL_PROMPT = """És o Diretor de Investigação da Equipa Elite do NoticIA. Falas directamente com Wilson — o teu editor e fundador.

IDENTIDADE:
Pensas como um editor de investigação de topo. Ouves o Wilson, avalias o potencial da pista, e dás a tua opinião honesta. És directo, sem rodeios — se uma pista não vale a pena, dizes.

IMPORTANTE — MUDANÇA V2:
Agora tens uma equipa REAL com pipeline de investigação. Quando Wilson quer uma investigação a fundo, diz-lhe para usar /investiga [tema]. Isso activa o pipeline completo:
1. TU decompões o pedido em tarefas de pesquisa
2. O REPORTER faz pesquisa OSINT real (Tavily, Exa, SEC EDGAR)
3. O FC FORENSE verifica cada facto de forma adversarial
4. O ESCRITOR redige o relatório com APENAS factos verificados

Em modo conversacional (sem /investiga), dás opiniões e orientação mas NÃO fazes investigação profunda.

ESTILO:
- Mensagens curtas e directas — sem paredes de texto
- PT-PT sempre
- Honesto: se não sabes, dizes que não sabes
- Se Wilson pede algo que requer investigação profunda, sugere /investiga
"""

# ── State ─────────────────────────────────────────────────────────────────────
conversations: dict[int, list[dict]] = {}
active_investigations: dict[int, str] = {}  # chat_id → investigation_id


def get_conversational_response(chat_id: int, user_message: str) -> str:
    """Get a conversational response from the Director (no investigation)."""
    if chat_id not in conversations:
        conversations[chat_id] = []

    conversations[chat_id].append({"role": "user", "content": user_message})
    history = conversations[chat_id][-20:]

    try:
        client = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key=OLLAMA_KEY)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": CONVERSATIONAL_PROMPT}] + history,
            temperature=0.7,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content or "..."
        conversations[chat_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        logger.error("LLM error: %s", e)
        return "Erro ao contactar o modelo. Tenta novamente."


async def send_telegram_message(bot, chat_id: int, text: str):
    """Send a message to Wilson, handling Telegram's 4096 char limit."""
    if len(text) <= 4096:
        await bot.send_message(chat_id, text, parse_mode="markdown")
    else:
        # Split by paragraphs first, then by char limit
        chunks = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > 4000:
                chunks.append(current)
                current = line
            else:
                current += "\n" + line if current else line
        if current:
            chunks.append(current)

        for chunk in chunks[:5]:
            try:
                await bot.send_message(chat_id, chunk, parse_mode="markdown")
            except Exception:
                # Fallback without markdown if parsing fails
                await bot.send_message(chat_id, chunk)


# ── Bot ───────────────────────────────────────────────────────────────────────
bot = TelegramClient("diretor_elite_bot", API_ID, API_HASH)


@bot.on(events.NewMessage(incoming=True))
async def handle_message(event):
    chat_id = event.chat_id
    sender = await event.get_sender()
    sender_id = sender.id if sender else 0

    if WILSON_ID and sender_id != WILSON_ID:
        logger.info("Mensagem ignorada de chat_id=%d (não é o Wilson)", sender_id)
        return

    text = event.raw_text.strip()
    if not text:
        return

    logger.info("Wilson [%d]: %s", chat_id, text[:80])

    # ── Command: /investiga ──────────────────────────────────────────
    if text.lower().startswith("/investiga"):
        query = text[len("/investiga"):].strip()
        if not query:
            await event.respond("Uso: /investiga [tema da investigação]")
            return

        if chat_id in active_investigations:
            await event.respond(
                "⚠️ Já tens uma investigação em curso. "
                "Espera que termine ou usa /cancela primeiro."
            )
            return

        # Import orchestrator here to avoid circular imports at module level
        from elite_orchestrator import run_investigation

        async def _send_update(cid, msg):
            try:
                await send_telegram_message(bot, cid, msg)
            except Exception as e:
                logger.warning("Failed to send update: %s", e)

        active_investigations[chat_id] = "starting"
        try:
            result = await run_investigation(query, chat_id, _send_update)
            if result.get("investigation_id"):
                active_investigations[chat_id] = result["investigation_id"]
        except Exception as e:
            logger.error("Investigation failed: %s", e)
            await event.respond(f"❌ Investigação falhou: {str(e)[:300]}")
        finally:
            active_investigations.pop(chat_id, None)
        return

    # ── Command: /injecta (V3) ───────────────────────────────────────
    if text.lower().startswith("/injecta"):
        args = text[len("/injecta"):].strip()
        if not args:
            await event.respond(
                "Uso: /injecta URL [contexto opcional]\n\n"
                "Exemplos:\n"
                "  /injecta https://exemplo.com/noticia\n"
                "  /injecta https://exemplo.com/noticia Ataque contra cristãos no Níger"
            )
            return

        # Parse URL and optional context
        parts = args.split(None, 1)
        url = parts[0]
        contexto = parts[1] if len(parts) > 1 else ""

        if not url.startswith("http"):
            await event.respond("⚠️ O primeiro argumento deve ser um URL válido (http/https).")
            return

        await event.respond(f"📥 A processar injecção editorial...\nURL: {url}")

        try:
            # Try to fetch content from URL
            title = contexto or url
            content_text = ""

            if httpx is not None:
                try:
                    resp = httpx.get(url, timeout=15, follow_redirects=True)
                    resp.raise_for_status()
                    html_text = resp.text

                    # Basic title extraction
                    import re as re_mod
                    title_match = re_mod.search(r'<title[^>]*>(.*?)</title>', html_text, re_mod.IGNORECASE | re_mod.DOTALL)
                    if title_match and not contexto:
                        title = title_match.group(1).strip()[:200]

                    # Basic content extraction (strip tags)
                    body_match = re_mod.search(r'<body[^>]*>(.*?)</body>', html_text, re_mod.IGNORECASE | re_mod.DOTALL)
                    if body_match:
                        raw = re_mod.sub(r'<[^>]+>', ' ', body_match.group(1))
                        content_text = re_mod.sub(r'\s+', ' ', raw).strip()[:3000]
                except Exception as fetch_err:
                    logger.warning("Injecta: falha a extrair conteudo de %s: %s", url, fetch_err)
                    content_text = contexto or "Conteudo nao extraido automaticamente"

            if not content_text:
                content_text = contexto or "Conteudo nao extraido automaticamente"

            # Insert directly into raw_events with source_type='editorial_injection'
            from supabase import create_client as sc
            sb = sc(SUPABASE_URL, SUPABASE_SERVICE_KEY)

            event_hash = hashlib.sha256(f"{url}:editorial_injection".encode()).hexdigest()
            title_normalized = re.sub(r"\s+", " ", title.lower().strip())
            title_hash = hashlib.md5(title_normalized.encode()).hexdigest()

            row = {
                "event_hash": event_hash,
                "title": title[:500],
                "title_hash": title_hash,
                "content": content_text[:5000],
                "url": url,
                "source_collector": "editorial_injection",
                "source_type": "editorial_injection",
                "raw_metadata": {
                    "injected_by": "wilson",
                    "contexto": contexto,
                    "via": "telegram_bot",
                    "injected_at": datetime.now(timezone.utc).isoformat(),
                },
                "processed": False,
            }

            result = sb.table("raw_events").upsert(
                row, on_conflict="event_hash", ignore_duplicates=False
            ).execute()

            if result.data:
                await event.respond(
                    f"✅ Injectado na pipeline!\n\n"
                    f"📰 *Titulo:* {title[:100]}\n"
                    f"🏷️ *Tipo:* editorial_injection\n"
                    f"📋 *Proximo passo:* Dispatcher → FC → Decisor → Escritor\n\n"
                    f"O artigo será processado nos proximos ~40 minutos."
                )
            else:
                await event.respond("⚠️ Inserção não retornou dados. Pode ser duplicado.")

        except Exception as e:
            logger.error("Injecta falhou: %s", e)
            await event.respond(f"❌ Falha na injecção: {str(e)[:200]}")
        return

    # ── Command: /status ─────────────────────────────────────────────
    if text.lower().startswith("/status"):
        if chat_id in active_investigations:
            inv_id = active_investigations[chat_id]
            await event.respond(f"🔄 Investigação em curso: `{inv_id}`")
        else:
            from supabase import create_client as sc
            sb = sc(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            result = sb.table("elite_investigations") \
                .select("id, status, wilson_query, global_confidence, created_at") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            if result.data:
                inv = result.data[0]
                await event.respond(
                    f"📊 Última investigação:\n"
                    f"Query: {inv['wilson_query'][:100]}\n"
                    f"Status: {inv['status']}\n"
                    f"Confiança: {inv.get('global_confidence', 'N/A')}\n"
                    f"Data: {inv['created_at'][:19]}"
                )
            else:
                await event.respond("Nenhuma investigação registada.")
        return

    # ── Command: /relatorio ──────────────────────────────────────────
    if text.lower().startswith("/relatorio"):
        from supabase import create_client as sc
        sb = sc(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table("elite_reports") \
            .select("title, markdown_content, summary_for_telegram, created_at") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        if result.data:
            report = result.data[0]
            md = report.get("markdown_content", "")
            if len(md) > 4000:
                # Send summary first, then chunks
                await event.respond(
                    f"📰 *{report['title']}*\n\n{report.get('summary_for_telegram', '')}"
                )
                chunks = [md[i:i+4000] for i in range(0, len(md), 4000)]
                for chunk in chunks[:5]:
                    await bot.send_message(chat_id, chunk)
            else:
                await event.respond(md or report.get("summary_for_telegram", "Relatório vazio."))
        else:
            await event.respond("Nenhum relatório disponível.")
        return

    # ── Command: /arquivo ────────────────────────────────────────────
    if text.lower().startswith("/arquivo"):
        from supabase import create_client as sc
        sb = sc(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table("elite_investigations") \
            .select("id, wilson_query, status, global_confidence, created_at") \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        if result.data:
            lines = ["📁 *Arquivo de Investigações:*\n"]
            for inv in result.data:
                conf = inv.get("global_confidence")
                conf_str = f" ({conf:.0%})" if conf else ""
                lines.append(
                    f"• [{inv['status']}]{conf_str} {inv['wilson_query'][:60]}\n"
                    f"  {inv['created_at'][:10]}"
                )
            await event.respond("\n".join(lines))
        else:
            await event.respond("Arquivo vazio.")
        return

    # ── Command: /cancela ────────────────────────────────────────────
    if text.lower().startswith("/cancela"):
        if chat_id in active_investigations:
            active_investigations.pop(chat_id, None)
            await event.respond("🛑 Investigação cancelada (nota: processos em curso podem continuar).")
        else:
            await event.respond("Nenhuma investigação activa para cancelar.")
        return

    # ── Conversational mode ──────────────────────────────────────────
    async with bot.action(chat_id, "typing"):
        reply = await asyncio.to_thread(get_conversational_response, chat_id, text)
    await event.respond(reply)
    logger.info("Diretor [%d]: %s", chat_id, reply[:80])


async def main():
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    logger.info("=" * 50)
    logger.info("Diretor Elite V3 Bot online: @%s", me.username)
    logger.info("Modelo conversacional: %s", MODEL)
    logger.info("Pipeline: Reporter → FC Forense → Escritor")
    if WILSON_ID:
        logger.info("Acesso restrito a Wilson (id=%d)", WILSON_ID)
    logger.info("=" * 50)
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
