# Diário de Bordo — Curador de Noticias

> Registo cronológico de todas as operações, incidentes, correcções e decisões.
> Actualizar sempre que houver alteração ao sistema.

---

## 2026-03-18 (Sessão 2 — Cowork)

### 15:00 UTC — Paperclip avaliado como orquestrador futuro (P3.5)

**O que é:** [Paperclip](https://paperclip.ing/) ([GitHub](https://github.com/paperclipai/paperclip)) — plataforma open-source (MIT, 4.3k stars) de orquestração de agentes como empresa. Node.js + React + PostgreSQL.
**Porque interessa:** Substitui pg_cron + APScheduler + Cowork tasks por camada unificada com org chart, heartbeats, budget enforcement, governance e audit trails.
**Decisão:** Adicionado ao plano como P3.5. Pode ser promovido a P2.1 se se saltar Procrastinate.
**Potencial:** Clipmart marketplace — NoticIA publicável como template "AI Newsroom".

### 14:30 UTC — Plano de Infraestrutura Robusta criado

**Ficheiro:** `docs/PLANO-INFRAESTRUTURA-ROBUSTA.md`
**Base:** Pesquisa LMNotebook (8 áreas) + Auditoria Cowork + APIs verificadas

**3 Fases, 16 items (agora 17 com Paperclip):**
- P1 (esta semana): Stored procedure atómica, heartbeats Better Stack, circuit breaker Tenacity+PyBreaker, alertas pg_cron→Telegram, gitleaks, idempotência
- P2 (este mês): Procrastinate (substituir APScheduler), CI/CD completo com rollback, testes mock LLM, trace IDs, Infisical secrets, Supabase Sentinel RLS
- P3 (trimestre): Separar containers, RunPod serverless, multi-idioma JSONB, Promptfoo evals

**Decisões arquitecturais:**
- Procrastinate em vez de Celery/Temporal (usa PostgreSQL existente, sem broker extra)
- Better Stack em vez de Datadog/Sentry (free tier adequado, heartbeat pattern)
- Stored Procedure PL/pgSQL em vez de 6 inserts separados (atomicidade garantida pelo Postgres)
- Infisical em vez de HashiCorp Vault (free tier, SDK Python, integra com Fly.io)

### 13:30 UTC — Fix Escritor: títulos incorrectos + fontes em falta (commit `4cbdc62`)

**Problema 1:** Artigo do Sporting tinha título "Bodø/Glimt avança para os quartos" — invertido.
**Causa:** Nemotron traduz literalmente o título da intake_queue sem verificar lógica.
**Fix:** Adicionadas regras explícitas ao prompt: "sujeito = protagonista", "nunca traduzir literalmente".

**Problema 2:** 4 artigos de hoje sem fontes (article_id = None após insert).
**Causa:** Primeiro fix removeu `.select("id")` mas PostgREST não devolve dados sem ele.
**Fix:** Insert separado do fetch: `insert()` → `select().eq(slug).single()`.
**Commit:** `4cbdc62` — deployed + Fly.io leases limpas.

**Título do Sporting corrigido directamente na DB:** "Sporting garante reviravolta épica e avança para os quartos da Liga dos Campeões"

### 13:00 UTC — Pipeline COMPLETA e a fluir ✅

**Estado final confirmado pelo Claude Code:**
- 486 raw_events na última hora (coletores RSS + GDELT activos)
- 6 artigos publicados nas últimas 2h
- 4 stages a funcionar: triagem (20min) → fact-checker (25min) → escritor (30min) → dossiê (6h)
- Telegram collector deploiado no Fly.io (`noticia-telegram`) — em flood-wait até ~16:30 UTC
- Máquina `0801e94c246168` started no `noticia-scheduler`

**Pendente:** Fix do escritor para inserir fontes (fetch ID separado após insert).
Sem este fix, artigos publicam-se mas sem fontes/claims ligados.

### 12:45 UTC — Bug Escritor: artigos sem fontes (causa-raiz definitiva)

**Problema:** 4 artigos publicados hoje sem fontes nem claims.
**Causa:** O fix anterior (remover `.select("id")` do insert) fez com que o PostgREST
não devolvesse o ID do artigo inserido. `article_id = None` → `_inserir_fontes_do_artigo()` nunca chamado.
**Fix:** Insert separado do fetch: `insert()` → `select().eq(unique_field).single()`.
Aplicado nos 3 inserts (articles por slug, sources por content_hash, claims por original_text).

### 12:20 UTC — Bug APScheduler: escritor nunca disparava

**Problema:** Triagem e fact-checker corriam mas o escritor nunca disparava. Zero menções nos logs.
**Causa:** `misfire_grace_time=1s` (default). Fact-checker e escritor com intervalo 30min
disparavam no mesmo instante. Fact-checker ganhava a thread, escritor era saltado silenciosamente.
**Fix:** `misfire_grace_time=120` + intervalos desfasados (triagem 20min, fact-checker 25min, escritor 30min).
**Commit:** `1c301d1`

### 11:45 UTC — Bug Escritor: `.select().single()` incompatível

**Problema:** O escritor (Fly.io) correu às 11:32 mas falhou em todos os artigos:
`'SyncQueryRequestBuilder' object has no attribute 'select'`

**Causa:** `escritor.py` usava `.insert({...}).select("id").single().execute()` — incompatível com supabase-py no Fly.io.
**Correcção:** Removido `.select("id").single()` em 3 inserts (articles, sources, claims).
**Commit:** `25593a5` → pushed + `fly deploy --app noticia-scheduler`

### 11:30 UTC — Telegram Collector: Deploy Fly.io (via Claude Code)

Deploy em curso pelo Claude Code usando `docs/PROMPT-FIX-TELEGRAM-FLYIO.md`.
App `noticia-telegram` criada, sessão Telethon a ser copiada para volume.

### 11:15 UTC — Telegram Collector: Faltava Fly.io

**Problema:** O `telegram-collector/` nunca foi deploiado no Fly.io. Corria apenas localmente no Mac.
Parou quando o Mac foi desligado/suspendido (último item: 17/03 16:38).

**Dados:**
- 1278 canais Telegram configurados (Tier 1-5, rotação por prioridade)
- 329 items inseridos na `intake_queue` (URLs `t.me/`)
- Insere DIRECTAMENTE na `intake_queue` (status='pending'), NÃO nos `raw_events`
- Usa Telethon (Telegram API), sessão autenticada em `sessions/curador_telegram.session`

**Correcções:**
1. Criado `telegram-collector/fly.toml` — app `noticia-telegram`, região `cdg`, volume para sessão
2. Actualizado `docs/PIPELINE-MAP.md` — corrigido fluxo (Telegram → intake_queue directo)
3. Actualizado `docs/DIARIO-DE-BORDO.md` — este registo

**Deploy pendente:**
```bash
cd telegram-collector
fly apps create noticia-telegram
fly volumes create telegram_sessions --region cdg --size 1 --app noticia-telegram
fly secrets set TELEGRAM_API_ID=... TELEGRAM_API_HASH=... SUPABASE_URL=... SUPABASE_SERVICE_KEY=... PUBLISH_API_KEY=... --app noticia-telegram
# Copiar sessão autenticada para o volume (uma vez):
fly ssh console --app noticia-telegram -C "mkdir -p /app/sessions"
# Depois: fly deploy --app noticia-telegram
```

### 11:05 UTC — Limpeza e Organização

**Acções:**
- Desactivado `collector-orchestrator` Cowork task (duplicava pg_cron jobs)
- 20 prompts antigos arquivados em `archive/prompts/`
- Criado `docs/` com: DIARIO-DE-BORDO.md, PIPELINE-MAP.md, ENGENHEIRO-CHEFE-PROMPT.md, auditorias/
- Raiz limpa: 6 ficheiros essenciais (CLAUDE.md, ARCHITECTURE-MASTER.md, ENGINEER-GUIDE.md, AGENT-PROFILES.md, FACT-CHECKING.md, ROADMAP.md)

### 10:45 UTC — Auditoria Pipeline Completa

**Diagnóstico:** Site sem notícias novas há 13h. Último artigo publicado: 2026-03-17 21:34 UTC.

**Mapa da pipeline (estado encontrado):**
```
STAGE 1: COLLECTORS → raw_events
├── collect-rss:     MORTO há 84h (desde 14/03 22:54) — sem pg_cron job
├── collect-gdelt:   MORTO há 113h (desde 13/03 18:04) — sem pg_cron job + bug JSON
├── collect-x-cowork: DESACTIVADO (task Cowork disabled)
├── collect-telegram: NUNCA CORREU (sem API key)
└── raw_events pendentes: 0

STAGE 2: BRIDGE (raw_events → intake_queue)
└── bridge-events pg_cron: ✅ A CORRER cada 20min — mas 0 eventos para processar

STAGE 3: TRIAGEM (pending → auditor_approved) — Fly.io DeepSeek V3.2
└── MORTO há 18h (desde 17/03 16:20)

STAGE 4: FACT-CHECK (auditor_approved → approved) — Fly.io Nemotron 3 Super
└── MORTO há 18h — 121 items encravados

STAGE 5: ESCRITOR (approved → published) — Fly.io Nemotron 3 Super
└── MORTO há 18h — 21 items prontos para publicar

STAGE 6: PUBLISHERS (Cowork tasks)
├── publisher-p2: ✅ A CORRER cada 3h
└── publisher-p3: ✅ A CORRER 08h/20h
```

**Causa-raiz 1 — Coletores sem pg_cron:**
Os Edge Functions `collect-rss` e `collect-gdelt` precisam de ser chamados periodicamente. Só existia 1 pg_cron job (`bridge-events`). Os coletores foram provavelmente chamados por Cowork tasks ou manualmente no passado, mas nunca tiveram pg_cron jobs permanentes. Quando as tasks foram migradas para Ollama/Fly.io, ninguém criou os jobs.

**Causa-raiz 2 — Fly.io scheduler crashou:**
O `scheduler_ollama.py` importava `telegram_editor.py` que dependia de `python-telegram-bot`. Quando o módulo foi removido (commit `21f4fd1` de hoje), o import crashava o scheduler inteiro. Triagem, fact-check e escritor pararam todos.

**Causa-raiz 3 — GDELT Edge Function bug:**
A API GDELT com `timespan=15min` devolvia texto em vez de JSON. O código fazia `res.json()` sem try-catch, crashando com "Unexpected token 'T'".

### 10:50 UTC — Correcções Aplicadas

1. **pg_cron job `collect-rss`** criado — `*/15 * * * *` (cada 15min)
2. **pg_cron job `collect-gdelt`** criado — `*/15 * * * *` (cada 15min)
3. **collect-gdelt Edge Function** redeployed (v7):
   - `timespan=15min` → `timespan=60min`
   - Adicionado try-catch para respostas non-JSON da API GDELT
4. **Trigger manual collect-rss** — resultado: 2003 novos raw_events
5. **Trigger manual collect-gdelt** — resultado: 50 novos raw_events
6. **Trigger manual bridge-events** — resultado: 20 novos items na intake_queue

**Estado após correcções:**
```
✅ raw_events: 2053 novos (RSS 2003 + GDELT 50)
✅ bridge-events: 20 novos pending na intake_queue
🔴 Fly.io scheduler AINDA PARADO — requer deploy manual
```

**Pendente:**
- [ ] Deploy Fly.io: `cd pipeline && fly deploy --app noticia-scheduler`
- [ ] Verificar que triagem/fact-check/escritor retomam processamento
- [ ] Confirmar artigos novos no site

---

## 2026-03-18 (Sessão 2 — Correcções Anteriores)

### Remoção da pipeline paralela Telegram Editor
- **Commit:** `21f4fd1`
- **Removido:** `telegram_editor.py` (600 linhas), `python-telegram-bot` do requirements
- **Simplificado:** `scheduler_ollama.py` — sem threading, sem bot, sleep loop simples
- **Motivo:** Pipeline paralela que bypassa intake_queue e quality gates

### Remoção de índice órfão
- **Removido:** `idx_intake_queue_writing` (filtrava `status='writing'` que já não existe)
- **Método:** Migration Supabase

### Remoção de fonte BBC 2025 incorrecta
- **Artigo:** Zelenskyy no Parlamento UK (evento 2026, fonte BBC de 2025)
- **Removido:** `claim_sources` + `sources` por SQL

---

## 2026-03-18 (Sessão 2 — Auditoria de Segurança)

### Fixes aplicados (commit `61bf8bb`):
| Fix | Descrição | Método |
|-----|-----------|--------|
| CRIT-002 | RLS activado em `publish_blocks`, `dossie_watchlist`, `instagram_posts` | Migration Supabase |
| CRIT-003 | `SET search_path = public` em 3 funções PL/pgSQL | Migration Supabase |
| CRIT-004 | Status `'writing'` removido do constraint intake_queue | Migration Supabase |
| CRIT-005 | Quality gate no escritor.py (certainty >= 0.7) | Código Python |
| HIGH-001 | RLS policies `auth.role()` → `(SELECT auth.role())` em 7 policies | Migration Supabase |
| HIGH-002 | Índices criados: intake_queue(status), articles(status), articles(created_at) | Migration Supabase |

---

## 2026-03-17 (Sessão 1 — Problemas Iniciais)

### Vercel deploy bloqueado 9h
- **Causa:** `vercel.json` com regex inválido (`(?:...)` non-capturing groups) em path-to-regexp
- **Fix:** Removidos os 2 headers problemáticos (imagens + JS/CSS) — redundantes com Next.js
- **Commit:** `6da44af`

### Pipeline não committed para git
- **Problema:** `triagem.py`, `fact_checker.py`, `escritor.py` modificados em Cowork mas nunca committed
- **Consequência:** Fly.io corria código antigo
- **Fix:** Commit `19ef60f` + push → GitHub Action deploy Fly.io

### Items stale na intake_queue
- **Encontrados:** 4 items `approved` com `data_real_evento` muito antigo (2025-11, 2026-02)
- **Fix:** SQL UPDATE → `status='fact_check'`, `error_message='stale_retroativo'`

### Staleness guard adicionado ao fact_checker
- `_extract_year_from_url()` — rejeita fontes com ano diferente do evento
- `_filter_stale_sources()` — aplica filtro antes de guardar fontes
- Tavily com `days: 30` para filtrar resultados recentes

---

## Cronologia Completa de pg_cron Jobs

| Job | Schedule | Criado em | Propósito |
|-----|----------|-----------|-----------|
| `bridge-events` | `*/20 * * * *` | Original | Ponte raw_events → intake_queue |
| `collect-rss` | `*/15 * * * *` | 2026-03-18 | Chama Edge Function collect-rss |
| `collect-gdelt` | `*/15 * * * *` | 2026-03-18 | Chama Edge Function collect-gdelt |

## Cowork Scheduled Tasks

| Task | Schedule | Estado | Propósito |
|------|----------|--------|-----------|
| `collector-orchestrator` | `*/20 * * * *` | ✅ Activo | Chama bridge-events + reporta estado |
| `publisher-p2` | `0 */3 * * *` | ✅ Activo | Publica artigos P2 |
| `publisher-p3` | `0 8,20 * * *` | ✅ Activo | Publica artigos P3 |
| `source-finder-cowork` | `0 7 * * *` | ✅ Activo | Descobre novas fontes RSS |
| `equipa-tecnica` | `0 */4 * * *` | ✅ Activo | Health checks (v1, será substituído por v2) |
| `cronista-semanal` | `0 20 * * 0` | ✅ Activo | Crónicas semanais (Domingos 20h) |
| `pipeline-triagem` | — | ⛔ Desactivado | Migrado para Ollama/Fly.io |
| `agente-fact-checker` | — | ⛔ Desactivado | Migrado para Ollama/Fly.io |
| `pipeline-escritor` | — | ⛔ Desactivado | Migrado para Ollama/Fly.io |
| `pipeline-orchestrator` | — | ⛔ Desactivado | Substituído |
| `pipeline-health-check` | — | ⛔ Desactivado | Substituído por equipa-tecnica |
| `article-processor` | — | ⛔ Desactivado | Deprecated |
| `collect-x-cowork` | — | ⛔ Desactivado | Sem API X oficial |
| `pipeline-verificacao` | — | ⛔ Desactivado | Substituído |

## Fly.io Scheduler (scheduler_ollama.py)

| Agente | Intervalo | Modelo | Função |
|--------|-----------|--------|--------|
| `run_triagem` | 20min | DeepSeek V3.2 (:cloud) | pending → auditor_approved/failed |
| `run_fact_checker` | 30min | Nemotron 3 Super (:cloud) | auditor_approved → approved/fact_check |
| `run_dossie` | 6h | Nemotron 3 Super (:cloud) | Pesquisa temas watchlist → pending |
| `run_escritor` | 30min | Nemotron 3 Super (:cloud) | approved → articles published |

---

*Última actualização: 2026-03-18 11:00 UTC*
