# Prompt para Claude Code — Configurar Agentes NoticIA no Paperclip

Lê primeiro: `CLAUDE.md`, `docs/PIPELINE-MAP.md`

---

## CONTEXTO

O Paperclip está instalado e a correr em `http://127.0.0.1:3100`.
A empresa "NoticIA" já está criada (company code: NOT).
Existem 2 agentes de teste (BuKi, BuKi 2) que devem ser removidos.

O objectivo é configurar os agentes REAIS da pipeline NoticIA.

**Supabase project ID:** `ljozolszasxppianyaac`
**Site:** `https://noticia-ia.vercel.app`
**Fly.io apps:** `noticia-scheduler` (pipeline LLM), `noticia-telegram` (collector)

---

## TAREFA 1 — Limpar agentes de teste

No dashboard do Paperclip (`http://127.0.0.1:3100/NOT/dashboard`):
1. Remove o agente "BuKi"
2. Remove o agente "BuKi 2"

---

## TAREFA 2 — Configurar Org Chart

Cria esta hierarquia de agentes:

```
CEO: Editor-Chefe (monitoriza tudo, aprova estratégia)
├── CTO: Engenheiro-Chefe (monitoriza pipeline, diagnostica problemas)
├── VP Colecta: (supervisiona coletores)
│   ├── Coletor RSS (adapter: http)
│   ├── Coletor GDELT (adapter: http)
│   ├── Coletor Telegram (adapter: http)
│   └── Bridge Events (adapter: http)
├── VP Editorial: (supervisiona pipeline de conteúdo)
│   ├── Triagem (adapter: process — chama Python via Fly.io)
│   ├── Fact-Checker (adapter: process)
│   ├── Escritor (adapter: process)
│   └── Dossiê (adapter: process)
└── VP Publicação: (supervisiona publishers e cronistas)
    ├── Publisher P2 (adapter: process ou http)
    ├── Publisher P3 (adapter: process ou http)
    └── 10 Cronistas (adapter: process)
```

---

## TAREFA 3 — Configurar cada Agente

### 3.1 Agentes HTTP (Coletores)

Estes são Edge Functions no Supabase chamadas via HTTP POST.

**Coletor RSS:**
- Adapter: `http`
- URL: `https://ljozolszasxppianyaac.supabase.co/functions/v1/collect-rss`
- Headers: `Authorization: Bearer sk-curador-199491851ad69d5c89c9bf07967272133dc65bec26315c6e0149094a90382b5e`
- Body: `{}`
- Heartbeat: `intervalSec: 900` (15 min)
- Role: "Recolhe notícias de 133 RSS feeds globais e insere em raw_events"

**Coletor GDELT:**
- Adapter: `http`
- URL: `https://ljozolszasxppianyaac.supabase.co/functions/v1/collect-gdelt`
- Headers: mesmas do RSS
- Body: `{}`
- Heartbeat: `intervalSec: 900` (15 min)
- Role: "Recolhe notícias da GDELT v2 API e insere em raw_events"

**Bridge Events:**
- Adapter: `http`
- URL: `https://ljozolszasxppianyaac.supabase.co/functions/v1/bridge-events`
- Headers: mesmas do RSS
- Body: `{}`
- Heartbeat: `intervalSec: 1200` (20 min)
- Role: "Ponte entre raw_events e intake_queue — scoring, dedup, prioridade"

**Coletor Telegram:**
- Adapter: `http` (health check do Fly.io)
- URL: `https://noticia-telegram.fly.dev/` (ou health endpoint se existir)
- Heartbeat: `intervalSec: 300` (5 min)
- Role: "Recolhe mensagens de 1278 canais Telegram e insere na intake_queue"
- NOTA: Este agente é monitorização apenas — o Fly.io já executa o collector automaticamente

### 3.2 Agentes Pipeline LLM

Estes correm no Fly.io `noticia-scheduler`. O Paperclip monitoriza-os (não executa directamente — o APScheduler no Fly.io trata da execução).

Para cada um, configurar como monitorização via heartbeat. Quando migrarmos para Paperclip como executor (fase 2), mudamos o adapter para `process` ou `claude_local`.

**Triagem:**
- Heartbeat: `intervalSec: 1200` (20 min)
- Role: "Classifica items da intake_queue por área, valida frescura. Modelo: DeepSeek V3.2"
- SOUL.md: "És o agente de triagem do NoticIA. Classifcas notícias por relevância para Portugal."

**Fact-Checker:**
- Heartbeat: `intervalSec: 1500` (25 min)
- Role: "Verifica factos com pesquisa web (Tavily/Exa/Serper). Modelo: Nemotron 3 Super"
- SOUL.md: "És o agente de verificação de factos. Procuras fontes primárias para cada afirmação."

**Escritor:**
- Heartbeat: `intervalSec: 1800` (30 min)
- Role: "Escreve artigos em PT-PT e publica via stored procedure atómica. Modelo: Nemotron 3 Super"
- SOUL.md: "És o escritor do NoticIA. Escreves artigos factuais em PT-PT rigoroso."

**Dossiê:**
- Heartbeat: `intervalSec: 21600` (6h)
- Role: "Pesquisa temas da watchlist (Cuba, Irão, Argentina, etc.) com web search"

### 3.3 Engenheiro-Chefe

- Adapter: `claude_local` (usa Claude Code CLI)
- Heartbeat: `intervalSec: 14400` (4h)
- Role: "Monitoriza pipeline, diagnostica problemas, alerta via Telegram"
- SOUL.md: Usar o conteúdo de `docs/ENGENHEIRO-CHEFE-PROMPT.md` (prompt completo com raciocínio)
- HEARTBEAT.md: A cada heartbeat, corre as queries de diagnóstico e envia relatório Telegram
- Tools: Supabase MCP, Vercel MCP, leitura de ficheiros

---

## TAREFA 4 — Configurar Alertas

No Paperclip Settings, configurar webhook para alertas quando um agente está DOWN:
- URL: `https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage`
- Body: `{"chat_id": "{TELEGRAM_ALERT_CHAT_ID}", "text": "🔴 Agente {{agent.name}} está DOWN no Paperclip"}`

---

## TAREFA 5 — Desactivar pg_cron (quando Paperclip assumir)

ATENÇÃO: Só desactivar DEPOIS de confirmar que o Paperclip está a chamar os endpoints correctamente.

```sql
-- No Supabase SQL Editor:
SELECT cron.unschedule('collect-rss');
SELECT cron.unschedule('collect-gdelt');
-- Manter bridge-events como backup por agora
```

---

## VALIDAÇÃO

- [ ] Dashboard mostra org chart com 4 níveis
- [ ] Heartbeats dos coletores HTTP a piscar verde
- [ ] Agentes de pipeline com status monitorizado
- [ ] Engenheiro-Chefe a correr via Claude Code CLI
- [ ] Alerta Telegram disparado ao pausar um agente manualmente
