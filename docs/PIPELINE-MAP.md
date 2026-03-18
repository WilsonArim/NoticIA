# Pipeline Map — Curador de Noticias

> Mapa completo do fluxo de dados, LLMs, crons e responsabilidades.
> Última actualização: 2026-03-18

---

## Fluxo de Dados (End-to-End)

```
FONTES GLOBAIS
      │
      ├─[pg_cron */15] collect-rss (Edge Function)   ──→ raw_events
      ├─[pg_cron */15] collect-gdelt (Edge Function)  ──→ raw_events
      ├─[Fly.io noticia-telegram] telegram-collector   ──→ intake_queue (DIRECTO, bypass raw_events)
      └─[desactivado] collect-x-cowork                ──→ raw_events
      │
      ▼
[pg_cron */20] bridge-events (Edge Function) ──→ raw_events → intake_queue (status='pending')
      │
      ▼
intake_queue (status='pending')
  ├── vindos do bridge-events (RSS + GDELT)
  └── vindos do telegram-collector (DIRECTO)
      │
      ▼
[Fly.io noticia-scheduler] triagem (cada 20min)     ──→ status='auditor_approved' ou 'auditor_failed'
      │
      ▼
[Fly.io noticia-scheduler] fact-checker (cada 30min) ──→ status='approved' ou 'fact_check'
      │
      ▼
[Fly.io noticia-scheduler] escritor (cada 30min)     ──→ articles (status='published')
      │
      ▼
[Cowork] publisher-p2 (cada 3h)  ──→ Vercel ISR revalidation
[Cowork] publisher-p3 (2x/dia)   ──→ Vercel ISR revalidation
      │
      ▼
SITE: https://noticia-ia.vercel.app
```

---

## Fly.io Apps (2 apps)

### App 1: `noticia-scheduler` (Pipeline LLM)

Região: `cdg` (Paris) | VM: 256MB shared | Dockerfile: `pipeline/Dockerfile`

| Agente | Intervalo | Modelo LLM | Função |
|--------|-----------|------------|--------|
| `run_triagem` | 20min | DeepSeek V3.2 (`:cloud`) | `pending` → `auditor_approved` / `auditor_failed` |
| `run_fact_checker` | 30min | Nemotron 3 Super (`:cloud`) | `auditor_approved` → `approved` / `fact_check` |
| `run_escritor` | 30min | Nemotron 3 Super (`:cloud`) | `approved` → `articles` (status=`published`) |
| `run_dossie` | 6h | Nemotron 3 Super (`:cloud`) | Pesquisa temas watchlist → `intake_queue` |

**Deploy:** `cd pipeline && fly deploy --app noticia-scheduler`

**Secrets:**
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`
- `TAVILY_API_KEY`, `EXA_API_KEY`, `SERPER_API_KEY`
- `MODEL_TRIAGEM`, `MODEL_FACTCHECKER`, `MODEL_ESCRITOR`, `MODEL_DOSSIE`

### App 2: `noticia-telegram` (Telegram Collector)

Região: `cdg` (Paris) | VM: 256MB shared | Dockerfile: `telegram-collector/Dockerfile`

| Processo | Intervalo | Tecnologia | Função |
|----------|-----------|------------|--------|
| `collector.py` | Ciclo cada 5min | Telethon (Telegram API) | Lê 1278 canais → `intake_queue` (DIRECTO) |

**Deploy:** `cd telegram-collector && fly deploy --app noticia-telegram`

**Secrets:**
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `PUBLISH_API_KEY`

**Volume:** `telegram_sessions` montado em `/app/sessions` (sessão Telethon persistente)

**Rotação de canais por tier:**
- Tier 1-2: TODOS os ciclos (5min)
- Tier 3-4: 1/3 por ciclo (rotação a cada 15min)
- Tier 5: 1/5 por ciclo (rotação a cada 25min)

---

## pg_cron Jobs (Supabase)

| Job | Schedule | Edge Function | Propósito |
|-----|----------|---------------|-----------|
| `collect-rss` | `*/15 * * * *` | `collect-rss` v8 | Recolhe RSS de 133 feeds → `raw_events` |
| `collect-gdelt` | `*/15 * * * *` | `collect-gdelt` v7 | Recolhe GDELT v2 API → `raw_events` |
| `bridge-events` | `*/20 * * * *` | `bridge-events` v7 | Ponte `raw_events` → `intake_queue` (scoring + dedup + prioridade) |

---

## Cowork Scheduled Tasks (Claude)

| Task | Schedule | Estado | Propósito |
|------|----------|--------|-----------|
| `publisher-p2` | `0 */3 * * *` | ✅ Activo | Publica artigos P2 cada 3h |
| `publisher-p3` | `0 8,20 * * *` | ✅ Activo | Publica artigos P3 às 8h e 20h |
| `source-finder-cowork` | `0 7 * * *` | ✅ Activo | Descobre novos RSS feeds diariamente |
| `equipa-tecnica` | `0 */4 * * *` | ✅ Activo | Health checks cada 4h (v1) |
| `cronista-semanal` | `0 20 * * 0` | ✅ Activo | Crónicas semanais dos 10 cronistas |
| `collector-orchestrator` | — | ⛔ Desactivado 18/03 | Substituído por pg_cron jobs |
| `pipeline-triagem` | — | ⛔ Desactivado | Migrado para Fly.io |
| `agente-fact-checker` | — | ⛔ Desactivado | Migrado para Fly.io |
| `pipeline-escritor` | — | ⛔ Desactivado | Migrado para Fly.io |
| `collect-x-cowork` | — | ⛔ Desactivado | Sem API X oficial |

---

## Modelos LLM

| Modelo | Provider | API Base | Usado por | Propósito | Tool Calling |
|--------|----------|----------|-----------|-----------|-------------|
| **DeepSeek V3.2** | Ollama Cloud | `ollama.com/v1` | Triagem | Classificação, scoring, frescura | Não |
| **Nemotron 3 Super** | Ollama Cloud | `ollama.com/v1` | Fact-checker | Verificação com web search | Sim (Tavily/Exa/Serper) |
| **Nemotron 3 Super** | Ollama Cloud | `ollama.com/v1` | Escritor | Redacção artigos PT-PT | Não |
| **Nemotron 3 Super** | Ollama Cloud | `ollama.com/v1` | Dossiê | Pesquisa temas watchlist | Sim (Tavily/Exa/Serper) |
| **Claude** | Anthropic | Cowork | Publishers, Equipa-técnica, Cronistas, Source-finder | Orquestração e análise | Sim (MCP) |

---

## Edge Functions (Supabase) — Activas

| Slug | Propósito | Trigger |
|------|-----------|---------|
| `collect-rss` | 133 RSS feeds → `raw_events` | pg_cron `*/15` |
| `collect-gdelt` | GDELT v2 API → `raw_events` | pg_cron `*/15` |
| `bridge-events` | Ponte `raw_events` → `intake_queue` | pg_cron `*/20` |
| `receive-article` | Recebe artigos → `articles` | Pipeline |
| `receive-claims` | Recebe claims extraídas | Pipeline |
| `receive-rationale` | Cadeias de raciocínio | Pipeline |
| `article-card` | Card OG para artigo | On-demand |
| `agent-log` | Logs dos agentes | Pipeline |
| `cronista` | Crónicas dos 10 cronistas | Cowork task |
| `collect-crawl4ai` | Enriquecimento on-demand | Manual |

---

## Status Transitions (intake_queue)

```
pending ──[triagem]──→ auditor_approved (score >= threshold)
                    └→ auditor_failed (rejeitado)

auditor_approved ──[fact-checker]──→ approved (certainty >= 0.70)
                                  └→ fact_check (rejeitado)

approved ──[escritor]──→ processed (artigo publicado em articles)

(estados terminais: auditor_failed, fact_check, failed, editor_rejected)
```

---

*Última actualização: 2026-03-18*
