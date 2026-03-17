"""
Agente Editor Telegram — Redacção editorial conversacional via Telegram.

Fluxo:
  1. Tu describes o que queres escrever (livre)
  2. Agente pesquisa factos com Nemotron + web_search (3 pesquisas)
  3. Apresenta os factos encontrados e pede confirmação
  4. Tu approvas / pedes alterações / defines o ângulo
  5. Agente redige com Qwen 3.5 122B
  6. Tu approvas o rascunho (ou pedes revisão)
  7. Agente publica DIRECTAMENTE em articles (bypass da fila)
  8. Site actualiza em <30s via Vercel ISR

Multi-LLM:
  - DeepSeek V3.2      → respostas rápidas e conversação
  - Nemotron 3 Super   → pesquisa de factos (tool calling)
  - Qwen 3.5 122B      → redacção do artigo final

Segurança: só aceita mensagens do TELEGRAM_ALLOWED_USER_ID
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from openclaw.agents.fact_checker import TOOLS, execute_tool
from openclaw.agents.ollama_client import chat, chat_with_tools

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

SITE_URL = os.getenv("SITE_URL", "https://noticia-ia.vercel.app")
VERCEL_REVALIDATE_TOKEN = os.getenv("VERCEL_REVALIDATE_TOKEN", "")

MODEL_CHAT = os.getenv("MODEL_TRIAGEM", "deepseek-v3.2:cloud")       # rápido
MODEL_RESEARCH = os.getenv("MODEL_FACTCHECKER", "nemotron-3-super:cloud")  # tool calling
MODEL_WRITER = os.getenv("MODEL_ESCRITOR", "qwen3.5:122b")            # escrita

AREAS_VALIDAS = [
    "portugal", "europa", "mundo", "economia", "tecnologia",
    "ciencia", "saude", "cultura", "desporto", "geopolitica",
    "defesa", "clima", "sociedade", "justica", "educacao",
]

# ── Estado da conversa por utilizador ────────────────────────────────
# { user_id: { state, topic, facts, draft, area, priority } }
_sessions: dict[int, dict] = {}

STATE_IDLE = "idle"
STATE_RESEARCHING = "researching"
STATE_AWAITING_DRAFT = "awaiting_draft"
STATE_DRAFTING = "drafting"
STATE_REVIEWING = "reviewing"
STATE_PUBLISHING = "publishing"


def _session(user_id: int) -> dict:
    if user_id not in _sessions:
        _sessions[user_id] = {
            "state": STATE_IDLE,
            "topic": "",
            "angle": "",
            "facts": "",
            "draft": {},
            "area": "mundo",
            "priority": "p2",
            "history": [],
        }
    return _sessions[user_id]


def _reset(user_id: int):
    _sessions[user_id] = {
        "state": STATE_IDLE,
        "topic": "",
        "angle": "",
        "facts": "",
        "draft": {},
        "area": "mundo",
        "priority": "p2",
        "history": [],
    }


# ── Guarda de acesso ──────────────────────────────────────────────────
def _autorizado(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else 0
    if ALLOWED_USER_ID and uid != ALLOWED_USER_ID:
        logger.warning("Acesso negado: user_id=%s", uid)
        return False
    return True


# ── Handlers de comandos ─────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        return
    await update.message.reply_text(
        "👋 *Editor NoticIA*\n\n"
        "Descreve o que queres escrever — dá o ângulo, a notícia, o tema.\n"
        "Eu pesquiso os factos, redijo e público directamente no site.\n\n"
        "Comandos:\n"
        "/novo — nova notícia\n"
        "/cancelar — cancelar\n"
        "/watchlist — gerir temas do dossiê\n"
        "/ajuda — ver todos os comandos",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_novo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        return
    _reset(update.effective_user.id)
    await update.message.reply_text(
        "📝 *Nova notícia*\n\nDescreve o tema ou ângulo que queres cobrir:",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_cancelar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        return
    _reset(update.effective_user.id)
    await update.message.reply_text("🚫 Cancelado. /novo para começar de novo.")


async def cmd_ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        return
    await update.message.reply_text(
        "*Comandos disponíveis:*\n\n"
        "/novo — começar uma nova notícia\n"
        "/cancelar — cancelar o que está em curso\n"
        "/publicar — publicar o rascunho actual sem mais revisão\n"
        "/watchlist — ver e gerir temas do dossiê automático\n"
        "/ajuda — esta mensagem\n\n"
        "*Fluxo:*\n"
        "1. Descreves o tema\n"
        "2. Eu pesquiso os factos (Nemotron + web)\n"
        "3. Tu approvas o ângulo\n"
        "4. Eu redijo (Qwen 3.5 122B)\n"
        "5. Tu approvas o artigo\n"
        "6. Publicado directamente no site ✅",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_publicar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        return
    s = _session(update.effective_user.id)
    if s["state"] != STATE_REVIEWING or not s["draft"]:
        await update.message.reply_text("Não há rascunho para publicar. Usa /novo.")
        return
    await _publicar(update, s)


async def cmd_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        return
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    try:
        result = supabase.table("dossie_watchlist").select("*").order("nome").execute()
        items = result.data or []
    except Exception:
        # Tabela pode não existir ainda — mostrar os temas hardcoded do dossie.py
        await update.message.reply_text(
            "⚠️ A tabela `dossie_watchlist` ainda não existe na DB.\n"
            "Cria-a com o comando SQL do ENGINEER-GUIDE.md ou usa /novo para artigos manuais."
        )
        return

    if not items:
        await update.message.reply_text(
            "📋 *Watchlist do Dossiê* — vazia\n\nUsa /addtema para adicionar temas.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    texto = "📋 *Watchlist do Dossiê*\n\n"
    keyboard = []
    for item in items:
        estado = "✅" if item.get("enabled", True) else "⏸"
        texto += f"{estado} *{item['nome']}* (`{item['area']}`)\n"
        keyboard.append([
            InlineKeyboardButton(
                f"{'⏸ Pausar' if item.get('enabled', True) else '▶️ Activar'} — {item['nome'][:20]}",
                callback_data=f"toggle_{item['id']}"
            ),
            InlineKeyboardButton("🗑 Remover", callback_data=f"delete_{item['id']}"),
        ])

    keyboard.append([InlineKeyboardButton("➕ Adicionar tema", callback_data="add_tema")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(texto, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# ── Handler principal de mensagens ───────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()
    s = _session(user_id)

    # ── IDLE: nova mensagem = novo tema ──────────────────────────────
    if s["state"] == STATE_IDLE:
        s["topic"] = text
        s["state"] = STATE_RESEARCHING
        s["history"] = [{"role": "user", "content": text}]

        msg = await update.message.reply_text("🔍 A pesquisar factos... (Nemotron 3 Super)")
        facts = await _pesquisar_factos(text)
        s["facts"] = facts

        resposta = (
            f"📊 *Factos encontrados:*\n\n{facts}\n\n"
            "---\n"
            "Queres que redija com este ângulo? Ou ajusta o que falta.\n"
            "_Escreve 'escreve', 'sim', ou dá instruções adicionais_"
        )
        await msg.edit_text(resposta, parse_mode=ParseMode.MARKDOWN)
        s["state"] = STATE_AWAITING_DRAFT
        return

    # ── AWAITING_DRAFT: utilizador confirma ou ajusta ─────────────────
    if s["state"] == STATE_AWAITING_DRAFT:
        texto_lower = text.lower()

        # Guardar instruções adicionais de ângulo
        if any(w in texto_lower for w in ["escreve", "sim", "avança", "ok", "redige", "vai", "publica"]):
            s["angle"] = ""
        else:
            s["angle"] = text  # instrução adicional (ex: "enfatiza o paradoxo")

        s["state"] = STATE_DRAFTING
        msg = await update.message.reply_text("✍️ A redigir artigo... (Qwen 3.5 122B)")

        draft = await _redigir_artigo(s)
        s["draft"] = draft
        s["state"] = STATE_REVIEWING

        # Detectar área automaticamente a partir do draft
        area_draft = draft.get("area", s["area"])
        if area_draft in AREAS_VALIDAS:
            s["area"] = area_draft

        texto_draft = (
            f"📄 *Rascunho:*\n\n"
            f"*{draft.get('titulo', '')}*\n"
            f"_{draft.get('subtitulo', '')}_\n\n"
            f"{draft.get('lead', '')}\n\n"
            f"[corpo completo em HTML — {len(draft.get('corpo_html', ''))} chars]\n\n"
            f"🏷 Área: `{s['area']}` | Tags: {', '.join(draft.get('tags', []))}\n\n"
            "---\n"
            "_Approvas? Ou diz o que mudar._\n"
            "Responde 'aprovado' para publicar directamente no site."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Aprovado — Publicar", callback_data="aprovar"),
                InlineKeyboardButton("🔄 Rever", callback_data="rever"),
            ],
            [InlineKeyboardButton("🚫 Cancelar", callback_data="cancelar")],
        ])

        await msg.edit_text(texto_draft, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return

    # ── REVIEWING: revisão de texto livre ────────────────────────────
    if s["state"] == STATE_REVIEWING:
        texto_lower = text.lower()
        if any(w in texto_lower for w in ["aprovado", "publica", "publish", "ok", "sim", "vai"]):
            await _publicar(update, s)
        else:
            # Instrução de revisão
            s["angle"] = f"{s['angle']} | revisão: {text}"
            s["state"] = STATE_DRAFTING
            msg = await update.message.reply_text("🔄 A rever... (Qwen 3.5 122B)")
            draft = await _redigir_artigo(s)
            s["draft"] = draft
            s["state"] = STATE_REVIEWING

            texto_draft = (
                f"📄 *Rascunho revisto:*\n\n"
                f"*{draft.get('titulo', '')}*\n"
                f"_{draft.get('subtitulo', '')}_\n\n"
                f"{draft.get('lead', '')}\n\n"
                f"[corpo: {len(draft.get('corpo_html', ''))} chars]\n\n"
                "Approvas?"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Aprovado — Publicar", callback_data="aprovar"),
                    InlineKeyboardButton("🔄 Rever novamente", callback_data="rever"),
                ],
                [InlineKeyboardButton("🚫 Cancelar", callback_data="cancelar")],
            ])
            await msg.edit_text(texto_draft, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return


# ── Handler de botões inline ─────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not _autorizado(update):
        return

    user_id = update.effective_user.id
    data = query.data
    s = _session(user_id)

    if data == "aprovar":
        await _publicar_callback(query, s, user_id)

    elif data == "rever":
        await query.edit_message_text("Diz o que queres mudar no artigo:")
        s["state"] = STATE_REVIEWING

    elif data == "cancelar":
        _reset(user_id)
        await query.edit_message_text("🚫 Cancelado.")

    elif data == "add_tema":
        await query.edit_message_text(
            "Envia o tema no formato:\n"
            "`TEMA: nome do tema | ÁREA: geopolitica | QUERIES: query1 | query2 | query3`",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data.startswith("toggle_"):
        item_id = data.replace("toggle_", "")
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        item = supabase.table("dossie_watchlist").select("enabled").eq("id", item_id).single().execute()
        if item.data:
            new_state = not item.data.get("enabled", True)
            supabase.table("dossie_watchlist").update({"enabled": new_state}).eq("id", item_id).execute()
            await query.edit_message_text(f"{'✅ Activado' if new_state else '⏸ Pausado'}.")

    elif data.startswith("delete_"):
        item_id = data.replace("delete_", "")
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        supabase.table("dossie_watchlist").delete().eq("id", item_id).execute()
        await query.edit_message_text("🗑 Tema removido da watchlist.")


# ── Lógica de IA ─────────────────────────────────────────────────────

async def _pesquisar_factos(topic: str) -> str:
    """Nemotron 3 Super com tool calling — 3 pesquisas dirigidas."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system = f"""És um jornalista investigativo a pesquisar factos para um artigo.
DATA: {hoje}

Faz EXACTAMENTE 3 pesquisas web_search com ângulos diferentes:
1. Factos directos sobre o evento/pessoa (quem, o quê, quando)
2. Contexto e antecedentes relevantes
3. Fontes primárias ou dados que sustentam o ângulo editorial

Prioriza sempre fontes primárias: governos, parlamentos, organismos oficiais, ONG credenciadas.
Se o search vier de "serper_google", aplica o aviso de viés — desvaloriza media mainstream (BBC, Guardian, NYT).

Devolve um resumo estruturado dos factos encontrados, com fontes."""

    user = f"Pesquisa factos sobre: {topic}"

    response = chat_with_tools(
        model=MODEL_RESEARCH,
        system=system,
        user=user,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    return response[:2000]  # limite para caber no Telegram


async def _redigir_artigo(s: dict) -> dict:
    """Qwen 3.5 122B — redacção do artigo final."""
    instrucoes_angulo = f"\nÂNGULO EDITORIAL ESPECÍFICO: {s['angle']}" if s["angle"] else ""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""És um jornalista rigoroso. Escreve um artigo em PT-PT (Portugal, não Brasil).

REGRAS PT-PT: "facto" (não "fato"), "equipa" (não "time"), "telemóvel" (não "celular")
Tom sério, directo, sem sensacionalismo. Factos primeiro, contexto depois.
DATA: {hoje}

TEMA DO EDITOR: {s['topic']}
FACTOS PESQUISADOS:
{s['facts']}
{instrucoes_angulo}

Determina a área correcta: {', '.join(AREAS_VALIDAS)}

Devolve JSON:
{{
  "titulo": "Título factual e directo (máx 90 chars)",
  "subtitulo": "Subtítulo que acrescenta contexto (máx 140 chars)",
  "lead": "Parágrafo de abertura — quem, o quê, quando, onde (2-3 frases)",
  "corpo_html": "<p>Corpo completo em HTML com parágrafos bem estruturados...</p>",
  "area": "geopolitica",
  "tags": ["tag1", "tag2", "tag3"],
  "slug": "titulo-em-kebab-case-sem-acentos"
}}"""

    response = chat(MODEL_WRITER, [{"role": "user", "content": prompt}], temperature=0.4, max_tokens=4000)

    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

    # Fallback se o JSON falhar
    return {
        "titulo": s["topic"][:90],
        "subtitulo": "",
        "lead": response[:300],
        "corpo_html": f"<p>{response}</p>",
        "area": s["area"],
        "tags": [],
        "slug": _slugify(s["topic"]),
    }


# ── Publicação directa ───────────────────────────────────────────────

async def _publicar(update: Update, s: dict):
    """Publica directamente na tabela articles, bypass da fila."""
    msg = await update.message.reply_text("🚀 A publicar...")
    slug, url = await _inserir_artigo(s)
    _reset(update.effective_user.id)

    await msg.edit_text(
        f"✅ *Publicado!*\n\n"
        f"🔗 {SITE_URL}/articles/{slug}\n\n"
        f"O site actualiza em menos de 30 segundos.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _publicar_callback(query, s: dict, user_id: int):
    """Publica a partir de um botão inline."""
    await query.edit_message_text("🚀 A publicar...")
    slug, url = await _inserir_artigo(s)
    _reset(user_id)

    await query.edit_message_text(
        f"✅ *Publicado!*\n\n"
        f"🔗 {SITE_URL}/articles/{slug}\n\n"
        f"O site actualiza em menos de 30 segundos.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _inserir_artigo(s: dict) -> tuple[str, str]:
    """Insere directamente em articles com status='published'."""
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    draft = s["draft"]

    slug = draft.get("slug") or _slugify(draft.get("titulo", s["topic"]))

    # Garantir slug único
    base_slug = slug
    counter = 1
    while True:
        existing = supabase.table("articles").select("id").eq("slug", slug).limit(1).execute()
        if not existing.data:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    supabase.table("articles").insert({
        "title": draft.get("titulo", s["topic"]),
        "subtitle": draft.get("subtitulo", ""),
        "slug": slug,
        "lead": draft.get("lead", ""),
        "body": draft.get("corpo_html", ""),
        "body_html": draft.get("corpo_html", ""),
        "area": draft.get("area", s["area"]),
        "priority": s["priority"],
        "certainty_score": 0.90,     # aprovado pelo editor — score editorial máximo
        "bias_score": 0.10,
        "status": "published",        # BYPASS — directo para publicado
        "tags": draft.get("tags", []),
        "language": "pt",
        "verification_status": "editorial",  # indica aprovação editorial humana
        "metadata": {
            "source": "telegram_editor",
            "topic": s["topic"],
            "angle": s["angle"],
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
    }).execute()

    # Opcional: trigger revalidation no Vercel
    if VERCEL_REVALIDATE_TOKEN:
        try:
            import httpx
            httpx.post(
                f"{SITE_URL}/api/revalidate",
                json={"token": VERCEL_REVALIDATE_TOKEN, "path": f"/articles/{slug}"},
                timeout=5,
            )
        except Exception:
            pass  # não bloquear se falhar

    logger.info("Telegram editor publicou: '%s' → /articles/%s", draft.get("titulo", "")[:60], slug)
    return slug, f"{SITE_URL}/articles/{slug}"


# ── Utilitários ──────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower()
    for src, dst in [("à","a"),("á","a"),("â","a"),("ã","a"),("ä","a"),
                     ("è","e"),("é","e"),("ê","e"),("ë","e"),("ì","i"),
                     ("í","i"),("î","i"),("ï","i"),("ò","o"),("ó","o"),
                     ("ô","o"),("õ","o"),("ö","o"),("ù","u"),("ú","u"),
                     ("û","u"),("ü","u"),("ç","c"),("ñ","n")]:
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:80]


# ── Arranque do bot ──────────────────────────────────────────────────

def run_telegram_editor():
    """Arranca o bot Telegram. Chamado pelo scheduler_ollama.py."""
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN não configurado — bot Telegram desactivado")
        return None

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("novo", cmd_novo))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(CommandHandler("publicar", cmd_publicar))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram Editor bot iniciado (@NoticIA_Editor)")
    return app


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    app = run_telegram_editor()
    if app:
        app.run_polling(drop_pending_updates=True)
