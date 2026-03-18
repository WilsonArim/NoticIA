# Setup Paperclip — Orquestração dos Agentes NoticIA

> Instalar Paperclip localmente e configurar a "empresa" NoticIA com todos os agentes.
> Isto substitui: APScheduler, Better Stack heartbeats, Procrastinate, e trace IDs manuais.

---

## Pré-requisitos

- Node.js 20+ (verificar: `node --version`)
- pnpm 9.15+ (instalar: `npm install -g pnpm`)
- Git

---

## Passo 1 — Instalar Paperclip (2 min)

```bash
# Opção A: Quick start
npx paperclipai onboard --yes

# Opção B: Clone manual (mais controlo)
cd ~
git clone https://github.com/paperclipai/paperclip.git
cd paperclip
pnpm install
pnpm dev
```

A API fica disponível em `http://localhost:3100`
O dashboard React em `http://localhost:3100` (ou porta configurada)

---

## Passo 2 — Criar a Empresa NoticIA PT

No dashboard do Paperclip ou via API:

**Company:**
- Name: `NoticIA PT`
- Mission: `Jornal independente, factual e sem viés. Farol contra fake news para o leitor português. Recolhe notícias globais, verifica factos, detecta viés, publica em PT-PT.`
- Budget: (configurar depois)

---

## Passo 3 — Criar os Agentes (Org Chart)

### Departamento: Colecta

| Agente | Role | Runtime | Heartbeat | Budget |
|--------|------|---------|-----------|--------|
| `coletor-rss` | Recolhe 133 RSS feeds e insere em raw_events | HTTP endpoint (`https://ljozolszasxppianyaac.supabase.co/functions/v1/collect-rss`) | 15 min | Grátis (Edge Function) |
| `coletor-gdelt` | Recolhe GDELT v2 API e insere em raw_events | HTTP endpoint (`https://ljozolszasxppianyaac.supabase.co/functions/v1/collect-gdelt`) | 15 min | Grátis (Edge Function) |
| `coletor-telegram` | Recolhe 1278 canais Telegram e insere em intake_queue | Fly.io app `noticia-telegram` (HTTP health check) | 5 min | Grátis (Fly.io) |
| `bridge-events` | Ponte raw_events → intake_queue (scoring + dedup) | HTTP endpoint (`https://ljozolszasxppianyaac.supabase.co/functions/v1/bridge-events`) | 20 min | Grátis (Edge Function) |

**Auth para HTTP endpoints:**
Header: `Authorization: Bearer {PUBLISH_API_KEY}`
Body: `{}`

### Departamento: Pipeline Editorial

| Agente | Role | Runtime | Heartbeat | Budget |
|--------|------|---------|-----------|--------|
| `triagem` | Classifica items, valida frescura, atribui score | Python script via Fly.io (ou Paperclip worker) | 20 min | ~$0 (DeepSeek V3.2 via Ollama Cloud) |
| `fact-checker` | Verifica factos com web search, atribui certainty/bias | Python script via Fly.io (ou Paperclip worker) | 25 min | ~$1-2/dia (Nemotron + Tavily) |
| `escritor` | Escreve artigos em PT-PT, publica via stored procedure | Python script via Fly.io (ou Paperclip worker) | 30 min | ~$0 (Nemotron via Ollama Cloud) |
| `dossie` | Pesquisa temas watchlist com web search | Python script via Fly.io | 6 horas | ~$0.5/dia (Nemotron + Tavily) |

**Modelos LLM:**
- Triagem: `deepseek-v3.2:cloud` (Ollama Cloud, `https://ollama.com/v1`)
- Fact-checker: `nemotron-3-super:cloud` (Ollama Cloud + Tavily/Exa/Serper)
- Escritor: `nemotron-3-super:cloud` (Ollama Cloud)
- Dossiê: `nemotron-3-super:cloud` (Ollama Cloud + Tavily)

### Departamento: Publicação

| Agente | Role | Runtime | Heartbeat | Budget |
|--------|------|---------|-----------|--------|
| `publisher-p2` | Publica artigos P2 cada 3h | Cowork Claude task | 3 horas | Grátis |
| `publisher-p3` | Publica artigos P3 às 8h/20h | Cowork Claude task | 12 horas | Grátis |
| 10x `cronista-*` | Crónicas semanais com personalidade | Cowork Claude task | Semanal (Domingos) | Grátis |
| `source-finder` | Descobre novos RSS feeds | Cowork Claude task | Diário (7h) | Grátis |

### Departamento: Engenharia

| Agente | Role | Runtime | Heartbeat | Budget |
|--------|------|---------|-----------|--------|
| `engenheiro-chefe` | Monitoriza pipeline, diagnostica problemas, alerta Telegram | Claude + Supabase MCP + Vercel MCP | 4 horas | Grátis |

---

## Passo 4 — Configurar Heartbeats

No Paperclip, cada agente tem um heartbeat schedule. Se um agente não reportar dentro do período + grace, o Paperclip marca-o como **DOWN** no dashboard.

Para os agentes HTTP (coletores), o Paperclip faz GET/POST ao endpoint e verifica o status.
Para os agentes Python (triagem/escritor), o Paperclip verifica se o último task completion foi recente.

**Configurar alertas:** Paperclip pode enviar webhooks quando um agente está DOWN. Configurar webhook para Telegram:
- URL: `https://api.telegram.org/bot{TOKEN}/sendMessage`
- Body: `{"chat_id": "{CHAT_ID}", "text": "🔴 Agente {agent_name} DOWN"}`

---

## Passo 5 — Migração Gradual

**Fase 1: Coletores (HTTP endpoints)**
Os coletores já são HTTP endpoints. Basta registar no Paperclip como agentes HTTP.
Desactivar os pg_cron jobs (`collect-rss`, `collect-gdelt`, `bridge-events`).
O Paperclip passa a chamar os mesmos endpoints nos heartbeats configurados.

**Fase 2: Pipeline LLM**
A triagem, fact-checker e escritor correm no Fly.io scheduler.
Opção A: Paperclip chama o Fly.io como HTTP endpoint (precisa de health endpoint).
Opção B: Mover os workers para dentro do Paperclip (Node.js workers que chamam os scripts Python).
Opção C: Manter Fly.io para execução mas o Paperclip para orquestração/monitorização.

**Recomendação:** Começar com Opção C — Paperclip monitoriza, Fly.io executa. Migrar para A/B depois.

**Fase 3: Cowork tasks**
Os publishers e cronistas correm no Cowork (Claude). O Paperclip pode monitorizá-los via heartbeat (o Cowork envia um ping ao Paperclip após cada execução).

---

## Passo 6 — Verificação

- [ ] Dashboard do Paperclip mostra todos os agentes
- [ ] Org chart com 4 departamentos
- [ ] Heartbeats a piscar verde para agentes activos
- [ ] Alerta Telegram quando se desactiva um agente manualmente
- [ ] Budget tracking por agente (se configurado)
- [ ] Audit trail mostra últimas execuções

---

## Supabase Connection

O Paperclip usa PostgreSQL embedded por defeito. Para produção, pode ligar ao Supabase:

```
DATABASE_URL=postgresql://postgres:{password}@db.ljozolszasxppianyaac.supabase.co:5432/postgres
```

**NOTA:** Verificar se o Supabase permite conexão directa (pooler mode vs direct). O Paperclip precisa de conexão directa para migrations.

---

## Deploy Produção (futuro)

Para correr 24/7:
- Docker: `docker compose up -d` (Dockerfile incluído no repo)
- Fly.io: Criar app `noticia-paperclip` separada
- VPS: Qualquer servidor com Node.js 20+ e PostgreSQL

---

## O que Desactivar Depois da Migração

| Componente | Acção |
|-----------|-------|
| pg_cron `collect-rss` | Desactivar (Paperclip assume heartbeat) |
| pg_cron `collect-gdelt` | Desactivar (Paperclip assume heartbeat) |
| pg_cron `bridge-events` | Desactivar (Paperclip assume heartbeat) |
| Fly.io `noticia-scheduler` APScheduler | Converter para worker simples (sem scheduler) |
| Cowork `equipa-tecnica` | Desactivar (Paperclip + Engenheiro-Chefe) |
| Cowork `collector-orchestrator` | Já desactivado |
| Better Stack | Não criar (Paperclip já tem heartbeats) |
| Procrastinate | Não implementar (Paperclip já tem task queue) |
