"""
Diretor Elite — Telegram Bot
============================
Interface conversacional entre Wilson e a Equipa Elite de Investigacao.
Usa Telethon (modo bot) + Ollama Cloud (mistral-large-3:675b).

Uso:
  cd ~/noticia/telegram-bot
  source .venv/bin/activate
  python bot.py

Requer no .env:
  TELEGRAM_API_ID=...
  TELEGRAM_API_HASH=...
  TELEGRAM_BOT_TOKEN=...   (obtido via @BotFather)
  OLLAMA_BASE_URL=https://ollama.com
  OLLAMA_API_KEY=...
  TELEGRAM_WILSON_CHAT_ID=...  (opcional — restringe acesso so ao Wilson)
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI
from telethon import TelegramClient, events

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
)
logger = logging.getLogger('diretor-elite-bot')

# ── Config ────────────────────────────────────────────────────────────────────
API_ID       = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH     = os.getenv('TELEGRAM_API_HASH', '')
BOT_TOKEN    = os.getenv('TELEGRAM_BOT_TOKEN', '')
OLLAMA_URL   = os.getenv('OLLAMA_BASE_URL', 'https://ollama.com')
OLLAMA_KEY   = os.getenv('OLLAMA_API_KEY', '')
MODEL        = os.getenv('MODEL_DIRETOR_ELITE', 'mistral-large-3:675b')
WILSON_ID    = int(os.getenv('TELEGRAM_WILSON_CHAT_ID', '0'))  # 0 = sem restricao

SYSTEM_PROMPT = """Es o Diretor de Investigacao da Equipa Elite do Curador de Noticias. Es o unico membro da equipa que fala directamente com Wilson — o teu editor e fundador. Os outros tres (reporter-investigacao, fc-forense, escritor-elite) trabalham nos bastidores sob a tua coordenacao.

IDENTIDADE:
Pensas como um editor de investigacao de topo. Ouves o Wilson, avalias o potencial da pista, defines a estrategia de investigacao, coordenas a equipa e trazes-lhe o resultado para aprovacao final. Es directo, honesto e sem rodeios — se uma pista nao vale a pena, dizes. Se vale, vas a fundo sem hesitar.

ESTILO DE COMUNICACAO NO TELEGRAM:
- Mensagens curtas e directas — sem paredes de texto
- Escreves como um colega de confianca, nao como um assistente
- PT-PT sempre
- Sem filtros para temas sensiveis — a tua missao e a verdade jornalistica

COMANDOS:
- "investiga [tema]" — inicias investigacao
- "como esta?" — status da investigacao em curso
- "muda [instrucao]" — feedback ao escritor-elite
- "publica" — accionar publisher (pede confirmacao)
- "cancela" — arquivar investigacao actual
- "arquivo" — listar investigacoes anteriores
"""

# ── Estado de conversacao por chat ────────────────────────────────────────────
conversations: dict[int, list[dict]] = {}

def get_llm_response(chat_id: int, user_message: str) -> str:
    if chat_id not in conversations:
        conversations[chat_id] = []

    conversations[chat_id].append({'role': 'user', 'content': user_message})

    # Manter contexto das ultimas 20 mensagens
    history = conversations[chat_id][-20:]

    try:
        client = OpenAI(
            base_url=f'{OLLAMA_URL}/v1',
            api_key=OLLAMA_KEY,
        )
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{'role': 'system', 'content': SYSTEM_PROMPT}] + history,
            temperature=0.7,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content or '...'
        conversations[chat_id].append({'role': 'assistant', 'content': reply})
        return reply
    except Exception as e:
        logger.error('LLM error: %s', e)
        return 'Erro ao contactar o modelo. Tenta novamente.'

# ── Bot ───────────────────────────────────────────────────────────────────────
bot = TelegramClient('diretor_elite_bot', API_ID, API_HASH)

@bot.on(events.NewMessage(incoming=True))
async def handle_message(event):
    chat_id = event.chat_id
    sender = await event.get_sender()
    sender_id = sender.id if sender else 0

    # Restricao ao Wilson (se configurado)
    if WILSON_ID and sender_id != WILSON_ID:
        logger.info('Mensagem ignorada de chat_id=%d (nao e o Wilson)', sender_id)
        return

    text = event.raw_text.strip()
    if not text:
        return

    logger.info('Wilson [%d]: %s', chat_id, text[:80])

    # Indicador de "a escrever..."
    async with bot.action(chat_id, 'typing'):
        reply = await asyncio.to_thread(get_llm_response, chat_id, text)

    await event.respond(reply)
    logger.info('Diretor [%d]: %s', chat_id, reply[:80])

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    logger.info('=' * 50)
    logger.info('Diretor Elite Bot online: @%s', me.username)
    logger.info('Modelo: %s', MODEL)
    if WILSON_ID:
        logger.info('Acesso restrito a Wilson (id=%d)', WILSON_ID)
    logger.info('=' * 50)
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
