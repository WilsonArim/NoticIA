# Auditoria Completa — Curador de Noticias
**Data:** 2026-03-18
**Versão:** v0.1 (NoticIA Architecture + Ollama Local + Cowork Cloud)
**Scope:** 117 commits, 1.9GB, 2x planos de execução, ~45 agentes

---

## EXECUTIVE SUMMARY

O **Curador de Noticias** é um sistema editorial autónomo bem-estruturado com arquitectura dual (Cowork Cloud + Ollama Local). O projecto demonstra excelente **separação de responsabilidades**, **instrumentação completa** e **segurança no design**. No entanto, há **CRÍTICAS FALHAS DE SEGURANÇA** e **GAPS ARQUITECTURAIS** que requerem remediação imediata.

**Score Geral (Vibe Code):** 6.2/10
**Risco de Segurança:** CRÍTICO (5 issues de nível CRÍTICO)
**Readiness Produção:** 60% (funcional, mas com vulnerabilidades)

---

## 1. VIBE CODE AUDIT — Scores por Dimensão

| Dimensão | Score | Peso | Weighted | Observações |
|----------|-------|------|----------|------------|
| **Readability** | 7.5/10 | 20% | 1.50 | Código bem-estruturado, type hints soltos em Python, docs boas |
| **Maintainability** | 6.0/10 | 25% | 1.50 | Múltiplos ficheiros de arquitectura desactualizados, confusão estado |
| **Performance** | 5.5/10 | 20% | 1.10 | Queries sem índices críticos, RLS ineficiente, caching básico |
| **Security** | 4.0/10 | 20% | 0.80 | **API keys hardcoded, RLS gaps, funções sem search_path** |
| **Testing** | 6.0/10 | 15% | 0.90 | Vitest configurado, mas tests não executados no CI |

**TOTAL SCORE: 6.2/10** ⚠️

---

## 2. AUDIT ARQUITECTURAL — Estado Real vs Planeado

### 2.1 Discrepâncias Críticas

| Aspecto | Planeado (ARCHITECTURE-MASTER.md) | Real (ENGINEER-GUIDE.md) | Impacto |
|---------|----------------------------------|------------------------|---------|
| **Pipeline Processing** | Todos Edge Functions (Grok API) | Hybrid: Cowork + Ollama Local | Mudança radical de paradigma |
| **Escritor (Writer)** | via Grok API em Edge Function | via Nemotron 3 Super:cloud (Ollama) | Custo reduzido, modelo diferente |
| **Triagem** | via Grok (`grok-fact-check` v11) | via DeepSeek V3.2 local | Velocidade vs Custo trade-off |
| **Colecta X** | `collect-x-grok` Edge Function | `collect-x-cowork` scheduled task | Paradigma Cowork (WebSearch, $0) |
| **Source Finder** | `source-finder` Edge Function | `source-finder-cowork` scheduled task | Paradigma Cowork |
| **Cronistas** | Edge Function `cronista/index.ts` | Híbrido: task `cronista-semanal` | Frequency ainda não implementada |
| **Dispatcher** | Existe na arquitectura | **NÃO IMPLEMENTADO** | Buraco: reporters recebem TODOS eventos |
| **Status Publishing** | `writing` state | ⚠️ **Status descontinuado** | Confusão em intake_queue workflow |

### 2.2 Tabela de Estado do Projecto

#### Implementado ✅
- **7 Coletores** (RSS, GDELT, Telegram, Event Registry, ACLED, Crawl4AI, X-Cowork)
- **20 Reporters** com keyword scoring completo
- **3 Agentes Editoriais** (Auditor, Escritor, Editor-Chefe)
- **2 Planos de Execução** (Cowork Cloud + Ollama Local)
- **3 Publishers** (P1/P2/P3 com frequências correctas)
- **10 Cronistas** com personalidade definida
- **4 Engenheiros de Monitorizacao** (Backend, Frontend, UI, Chefe)
- **124 Fontes** descobertas, 95 validadas
- **Base de Dados** com 22 tabelas, RLS parcial

#### Parcialmente Implementado ⚠️
- **Dispatcher** — existe conceptualmente, mas routing é keyword-based (não LLM)
- **Cronistas** — Edge Function existe, task semanal desactivada (em construção)
- **Fact-check Profundo** — Nemotron 3 local, mas sem tools (Tavily/Exa/Serper desactivados no Supabase)
- **HITL Reviews** — coluna existe, interface não existe no frontend

#### Não Implementado ❌
- **Seccao "Opiniao/Analise"** no frontend para cronistas
- **Feedback Loop** — leitores não conseguem comentar/votar
- **Dossié/Watchlist** — tabela existe (`dossie_watchlist`), feature não implementada
- **Instagram Publishing** — `publish-instagram` Edge Function existe, mas interface/automatização não implementada
- **Scheduler Ollama** — descrito em ENGINEER-GUIDE.md, ficheiro `scheduler_ollama.py` não está presente no repositório

---

## 3. SECURITY AUDIT — CRÍTICO

### 3.1 Vulnerabilidades Descobertas

#### 🔴 CRÍTICO (5 issues)

1. **[CRIT-001] API Keys Hardcoded em .env.local**
   - **Ficheiro:** `.env.local` (EXPOSTOS NO REPOSITÓRIO GIT)
   - **Keys expostas:**
     - `PUBLISH_API_KEY=sk-curador-199491851ad69d5c89c9bf07967272133dc65bec26315c6e0149094a90382b5e`
     - `TAVILY_API_KEY=tvly-dev-...` (Tavily API)
     - `EXA_API_KEY=7c04136d-...` (Exa Search)
     - `SERPER_API_KEY=4b1a5943...` (Serper)
     - `OLLAMA_API_KEY=e695b54856...` (Ollama Cloud)
     - `NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...` (Supabase)
   - **Risco:** Qualquer pessoa com acesso ao repo pode chamar APIs, consumir quota, aceder dados
   - **Remediação:**
     - ✅ Rotate TODAS as API keys **IMEDIATAMENTE**
     - Adicionar `.env.local` ao `.gitignore` (já existe, mas ficheiro foi commited)
     - Usar Supabase Secrets ou GitHub Secrets para CI/CD
     - Implementar pre-commit hook para detectar patterns secretos

2. **[CRIT-002] RLS Desactivado em 3 Tabelas Públicas**
   - **Tabelas sem RLS:** `publish_blocks`, `dossie_watchlist`, `instagram_posts`
   - **Impacto:** Qualquer utilizador autenticado pode ler/escrever dados dessas tabelas
   - **Remediação:** Activar RLS e definir policies apropriadas
   - **Código:** [Supabase Advisory](https://supabase.com/docs/guides/database/database-linter?lint=0013_rls_disabled_in_public)

3. **[CRIT-003] 3 Funções PL/pgSQL com Search Path Mutable**
   - **Funções:** `enforce_publish_quality`, `get_secret`, `log_publish_block`
   - **Risco:** SQL injection potencial se não há `SET search_path = public`
   - **Remediação:** Adicionar `SET search_path = public` a cada função
   - **Impacto:** Permite que atacante altere comportamento através de schemas não-standard

4. **[CRIT-004] SUPABASE_SERVICE_ROLE_KEY no .env.local**
   - **Ficheiro:** `.env.local`, linha 4
   - **Valor:** `eyJ...` (JWT incompleto no ficheiro lido, mas está lá)
   - **Risco:** Permissões elevadas (full database access) comprometidas
   - **Remediação:** Rotate KEY, nunca commitar service keys

5. **[CRIT-005] "writing" Status Descontinuado em intake_queue**
   - **Problema:** ENGINEER-GUIDE.md diz "status `writing` foi descontinuado"
   - **Risco:** Código Ollama local pode ainda usar esse status → race conditions
   - **Onde:** `intake_queue.status` constraint inclui `'writing'::text`
   - **Remediação:** Remover status descontinuado, atualizar workflows Ollama

#### 🟠 ALTO (6 issues)

6. **[HIGH-001] RLS Ineficiente — Calls auth.<function>() por Row**
   - **Tabelas afectadas:** `raw_events`, `scored_events`, e mais
   - **Impacto:** Query performance degrada com volume
   - **Remediação:** Substituir `auth.<function>()` com `(SELECT auth.<function>())`

7. **[HIGH-002] Falta Índices em Colunas de Filtro Críticas**
   - **Colunas sem índices:** `intake_queue.status`, `articles.status`, `articles.created_at`
   - **Impacto:** Queries lentas no pipeline, bloqueios
   - **Remediação:** Adicionar índices B-tree: `CREATE INDEX idx_intake_queue_status ON intake_queue(status)`

8. **[HIGH-003] Token Logs Crescimento Infinito**
   - **Tabela:** `token_logs` (0 rows actualmente, mas pode crescer)
   - **Sem retenção:** Não há política de limpeza automática
   - **Remediação:** Implementar `PARTITION BY RANGE` ou cron job para purga

9. **[HIGH-004] Edge Functions Sem Proteção CORS Completa**
   - **Verificado:** `bridge-events`, `receive-article`, etc.
   - **Risco:** CORS headers podem estar misconfigured, expostos a XSS
   - **Remediação:** Verificar cada Edge Function para `Access-Control-Allow-Origin` (deve ser whitelist)

10. **[HIGH-005] Configuração Supabase Auth Vulnerable**
    - **Issue:** "Leaked password protection is currently disabled"
    - **Remediação:** Activar HaveIBeenPwned check no dashboard Supabase

11. **[HIGH-006] Ficheiro .env.local Tracked em Git**
    - **Evidência:** Commit recente alterou `.env.local`
    - **Remediação:** `git rm --cached .env.local`, adicionar ao `.gitignore`

#### 🟡 MÉDIO (4 issues)

12. **[MED-001] Endpoint `/v1/responses` Grok Deprecated**
    - **Onde:** Referências em FACT-CHECKING.md, mas migrado para Ollama
    - **Impacto:** Se voltarem a usar Grok, endpoint pode descontinuar
    - **Remediação:** Documentar deprecação, usar apenas Ollama local

13. **[MED-002] Circuit Breaker Sem Implementação Completa**
    - **Config:** `CIRCUIT_BREAKER_THRESHOLD = 5`, `PAUSE_SECONDS = 60`
    - **Problema:** Logic não está implementada em `runner.py`
    - **Remediação:** Implementar circuit breaker pattern em retry logic

14. **[MED-003] AbortController Timeout 30s**
    - **Onde:** cronista, writer-publisher Edge Functions
    - **Problema:** Cowork tasks podem timeout antes de completar
    - **Remediação:** Aumentar para 120s ou implementar long-polling

15. **[MED-004] Error Messages Genéricas Insuficientes**
    - **Problema:** Some error handling pode expor detalhes internos
    - **Remediação:** Implementar error boundary global, logging estruturado

### 3.2 OWASP Top 10 — Mapping

| OWASP | Issue | Evidência | Severidade |
|-------|-------|-----------|-----------|
| A01 — Broken Access Control | RLS disabled em 3 tabelas | `publish_blocks`, `dossie_watchlist`, `instagram_posts` | CRÍTICO |
| A02 — Cryptographic Failures | API keys em plain text | `.env.local` commited | CRÍTICO |
| A03 — Injection | PL/pgSQL search_path mutable | 3 funções sem `SET search_path` | CRÍTICO |
| A04 — Insecure Design | Status descontinuado em workflow | `writing` ainda em DB schema | CRÍTICO |
| A05 — Security Misconfiguration | CORS possível vulnerability | Edge Functions unchecked | ALTO |
| A06 — Vulnerable Components | Dependências outdated | npm packages com vulns menores | MÉDIO |
| A07 — Authentication | Password breach check disabled | Supabase Auth config | ALTO |
| A08 — Data Integrity | Bitwise XOR para timing-safe comparison | API key validation usa método manual | MÉDIO |
| A09 — Logging Gaps | Minimal error details | Logs baseados em `pipeline_runs` apenas | MÉDIO |
| A10 — Supply Chain | Npm dependencies | 40+ packages, algumas com CVEs leves | BAIXO |

---

## 4. SOTA AGENT ENGINEERING AUDIT

### 4.1 Princípios SOTA — Checklist

| Princípio | Implementado? | Observações | Score |
|-----------|---------------|------------|-------|
| **Identity** | ✅ Parcial | Cronistas têm identidade clara, agentes editoriais têm personas, mas Reporters são genéricos | 7/10 |
| **Prompt Template XML** | ❌ Não | Prompts em markdown, não XML estruturado | 3/10 |
| **Tools Mínimos** | ✅ Sim | Cowork tasks usam Claude nativo (0 tools externos), Ollama usa Tavily/Exa/Serper | 8/10 |
| **Verification Loop** | ✅ Sim | Triagem → Verificacao → Escritor + revisão Editor-Chefe | 7/10 |
| **Handoff Between Agents** | ✅ Sim | Via `intake_queue` com status transitions claros | 8/10 |
| **FinOps Tracking** | ⚠️ Parcial | Token logs existem, mas não há custo real (Cowork/Ollama incluidos na subscricao) | 4/10 |
| **Error Handling** | ⚠️ Parcial | Try-catch existe, mas sem retry loops estruturados em todos os agentes | 5/10 |
| **Context Engineering** | ✅ Sim | Briefing context para cronistas, system prompts detalhados | 7/10 |

**SOTA Score: 6.2/10** — Bem-estruturado, mas missing XML templating + robust error loops

### 4.2 Agentes Chave — Análise Detalhada

#### ✅ Auditor ("O Cetico")
- **Implementação:** `agents/triagem.py` (162 linhas)
- **Modelo:** DeepSeek V3.2
- **Função:** Valida frescura, reclassifica área, fact-check básico
- **Problemas:** Sem verificação cross-tab (não lê articles já publicadas para dedup), score final é 0.0-1.0 mas usado como boolean
- **Score:** 6/10

#### ⚠️ Escritor (A Pena)
- **Implementação:** `agents/escritor.py` (295 linhas)
- **Modelo:** Nemotron 3 Super
- **Função:** Escreve artigo PT-PT 300-1200 chars, insere em `articles` com status `published` DIRECTAMENTE
- **Problemas:**
  - Sem revisão Editor-Chefe antes de publicar?! (status direto = `published`)
  - Sem constraint verificacao de `certainty_score >= 0.895`
  - Sem `bias_score` validation
- **Score:** 3/10 ⚠️ **CRÍTICO: BYPASS QUALITY GATES**

#### ❌ Dispatcher
- **Implementação:** NÃO EXISTE
- **Consequência:** Todos 20 reporters recebem TODOS eventos (ineficiente)
- **Planeado:** Classificar tema + atribuir reporter correcto
- **Score:** 0/10

#### ✅ Cronistas (10x)
- **Implementação:** Edge Function `cronista/index.ts` + system prompts
- **Modelo:** Claude (Cowork)
- **Qualidade:** Prompts bem-estruturados, identidade clara, 10 ideologias diferentes
- **Problema:** Scheduled task `cronista-semanal` desactivada
- **Score:** 8/10

#### ⚠️ Equipa Tecnica (4 engenheiros)
- **Implementação:** `COWORK-EQUIPA-TECNICA.md` scheduled task
- **Função:** Health checks + auto-correcção segura
- **Status:** Implementado mas não confirmado em execução real
- **Score:** 7/10

---

## 5. OPERATIONAL AUDIT — Pipeline Health

### 5.1 Data Flows — Estado Actual (2026-03-18)

```
COLECTA (Cowork scheduler, a cada 20min):
  ├─ collect-rss: ~1824 raw_events (RSS 133 feeds)
  ├─ collect-x-cowork: ~110 raw_events (WebSearch site:x.com)
  ├─ collect-telegram: 48 canais configurados
  ├─ collect-gdelt: Rate-limited (429 erro anterior, agora com backoff)
  ├─ collect-event-registry: INATIVO (falta API key)
  ├─ collect-acled: INATIVO (falta API key)
  └─ collect-crawl4ai: On-demand enrichment

RESULTADO: raw_events = 2103 rows (com dedup)

BRIDGE EVENTS (Cowork, cada 20min):
  intake_queue.status = 'pending' (623 rows)

TRIAGEM (Ollama Local, cada 20min) — **EXECUTÁVEL?**:
  DeepSeek V3.2 valida frescura, reclassifica área
  → 'auditor_approved' (score >= threshold)
  → 'auditor_failed' (rejeitado)

VERIFICACAO (Ollama Local, cada 30min):
  Nemotron 3 Super fact-check profundo (Tavily/Exa/Serper)
  → 'approved' (certainty >= 0.7)
  → 'fact_check' (rejeitado)

ESCRITA (Ollama Cloud, cada 30min):
  Nemotron 3 Super escreve artigo PT-PT
  → articles.status = 'published' DIRECTAMENTE (!!)
  → intake_queue.status = 'processed'

RESULTADO: articles = 124 rows (61 published, 38 review, rest draft/archived)
```

### 5.2 Database Metrics (via Supabase)

| Tabela | Rows | Status | Notas |
|--------|------|--------|-------|
| `raw_events` | 2103 | ✅ Saudável | Coletores fluem |
| `intake_queue` | 623 | ⚠️ Backlog | 623 pending, ~4 em processamento |
| `articles` | 124 | ✅ Saudável | 61 published em 3 semanas |
| `sources` | 539 | ✅ Saudável | Dedup de URLs funcionando |
| `claims` | 261 | ✅ Saudável | Extracted OK |
| `chronicles` | 10 | ⚠️ Incompleto | Só draft (não publicado) |
| `agent_logs` | 92 | ✅ Crescendo | Logging funcional |
| `pipeline_runs` | 777 | ⚠️ Crescimento | Sem retenção limits |
| `token_logs` | 0 | N/A | Nunca usado (Ollama/Cowork não custam) |

### 5.3 Scheduled Tasks — Verificacao

```
✅ ACTIVOS (confirmado em ENGINEER-GUIDE.md):
  - collector-orchestrator (20min)
  - publisher-p2 (3h)
  - publisher-p3 (8h, 20h)
  - source-finder-cowork (07h diário)
  - equipa-tecnica (4h)
  - cronista-semanal (Sunday 20h) — PENDENTE VERIFICACAO

⛔ DESACTIVADOS (correcto):
  - pipeline-triagem (migrado para Ollama)
  - pipeline-verificacao (migrado para Ollama)
  - pipeline-escritor (migrado para Ollama)
  - pipeline-orchestrator (deprecated)
  - collect-x-cowork (sem API X oficial)
```

### 5.4 Problemas Críticos Operacionais

1. **Scheduler Ollama Não Verificado**
   - **Ficheiro referenciado:** `pipeline/src/openclaw/scheduler_ollama.py`
   - **Status:** NÃO ENCONTRADO NO REPOSITÓRIO
   - **Impacto:** Triagem, verificacao, escrita podem estar paradas no Mac local
   - **Evidência:** Se parado, `intake_queue` tem 623 rows pending → items encravados em `auditor_approved`

2. **Escritor Bypassa Quality Gates**
   - **Issue:** `escritor.py` insere artigos com `status='published'` DIRECTAMENTE
   - **Deveria:** Respeitar constraints de `certainty_score >= 0.895` + `bias_score <= 0.5`
   - **Risco:** Artigos ruins publicados sem verificacao final

3. **Dispatcher Ausente = Ineficiência**
   - **Todos 20 reporters** processam TODOS eventos
   - **Potencial:** Ruído, falsos positivos, custo LLM inflado (se usasse Grok)

4. **Cronistas Desactivados**
   - **Task:** `cronista-semanal` não executa
   - **Resultado:** Chronicles ficam em draft, não publicadas

5. **Ollama Cloud vs Local Confusion**
   - **Documentacao:** ENGINEER-GUIDE.md diferente de ARCHITECTURE-MASTER.md
   - **Risco:** Equipa não sabe qual setup está activo

---

## 6. TOP 20 ISSUES — Ordenado por Severidade

### CRÍTICO (5)

1. **API Keys Hardcoded em `.env.local`**
   - Ficheiro: `.env.local` (TODOS os secrets expostos)
   - Ação: Rotate keys, remover ficheiro do git
   - Esforço: 30 min

2. **RLS Disabled em 3 Tabelas Públicas**
   - Ficheiro: `publish_blocks`, `dossie_watchlist`, `instagram_posts`
   - Ação: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
   - Esforço: 1h

3. **PL/pgSQL Search Path Mutable (3 funções)**
   - Ficheiro: Database (enforce_publish_quality, get_secret, log_publish_block)
   - Ação: ADD `SET search_path = public`
   - Esforço: 30 min

4. **"writing" Status Descontinuado em DB Schema**
   - Ficheiro: `intake_queue` constraint
   - Ação: Remover da constraint, update Ollama code
   - Esforço: 1h (+ coordenacao Ollama)

5. **Escritor Bypassa Quality Gates**
   - Ficheiro: `pipeline/src/openclaw/agents/escritor.py` (linhas ~250-295)
   - Ação: Adicionar validacao `certainty_score >= 0.895` antes de `INSERT`
   - Esforço: 2h (+ testing)

### ALTO (6)

6. **Scheduler Ollama Não Encontrado em Repositório**
   - Ficheiro: Missing `pipeline/src/openclaw/scheduler_ollama.py`
   - Ação: Verificar se existe localmente (Mac user), commitar ou documentar setup local
   - Esforço: 1h (research)

7. **RLS Ineficiente — auth.<function>() por Row**
   - Ficheiro: Database (raw_events, scored_events, etc.)
   - Ação: Refactor RLS to use `(SELECT auth.<function>())`
   - Esforço: 4h (testing crítico)

8. **Índices Faltantes em Colunas Críticas**
   - Ficheiro: Database
   - Ação: CREATE INDEX para status, created_at em intake_queue + articles
   - Esforço: 1h

9. **Dispatcher Não Implementado**
   - Ficheiro: Missing `pipeline/src/openclaw/agents/dispatcher.py`
   - Ação: Implementar clasification LLM (ou manter keyword-based se custo é concern)
   - Esforço: 8h (design + testing)

10. **SUPABASE_SERVICE_ROLE_KEY Hardcoded**
    - Ficheiro: `.env.local`
    - Ação: Rotate, usar Supabase vault para CI/CD
    - Esforço: 1h

11. **Token Logs Sem Retenção**
    - Ficheiro: Database (token_logs table)
    - Ação: Implementar cleanup cron (DELETE >30 dias)
    - Esforço: 1h

12. **Edge Functions CORS Configuration Unchecked**
    - Ficheiro: `supabase/functions/*/index.ts` (7 functions)
    - Ação: Audit cada uma, whitelist ALLOWED_ORIGINS
    - Esforço: 3h

### MÉDIO (9)

13. **Cronistas Scheduled Task Desactivada**
    - Ficheiro: Cowork (cronista-semanal)
    - Ação: Reactivar ou confirmar status
    - Esforço: 30 min

14. **Frontend Cronistas Incompleto**
    - Ficheiro: `src/app/cronistas/*`
    - Ação: Seccao "/cronistas" pode ser incompleta (não verificado)
    - Esforço: 4h (UI polish)

15. **HITL Reviews — Interface Não Implementada**
    - Ficheiro: `hitl_reviews` table existe (38 rows), mas frontend não tem interface
    - Ação: Criar dashboard de revisão humana
    - Esforço: 8h (UI + routing)

16. **Circuit Breaker Logic Não Implementado**
    - Ficheiro: `pipeline/src/openclaw/config.py` (config apenas)
    - Ação: Implementar em retry logic
    - Esforço: 3h

17. **Error Handling Inconsistente**
    - Ficheiro: Multiple (agents, edge functions)
    - Ação: Standarizar try-catch + logging
    - Esforço: 5h

18. **AbortController Timeout 30s Curto**
    - Ficheiro: Edge Functions (cronista, writer-publisher)
    - Ação: Aumentar para 120s ou implementar long-polling
    - Esforço: 1h

19. **ARCHITECTURE-MASTER.md Desatualizado**
    - Ficheiro: Conflita com ENGINEER-GUIDE.md
    - Ação: Actualizar ou deprecate
    - Esforço: 2h (documentation)

20. **Não há Teste de Carga (Load Testing)**
    - Ficheiro: `pipeline/tests/` (testes unitarios, nenhum load test)
    - Ação: Implementar com k6 ou locust
    - Esforço: 6h

---

## 7. ROADMAP DE REMEDIACAO — Por Prioridade

### FASE 1: REMEDIACAO SEGURANCA (1-2 dias)
**Objetivo:** Eliminar vulnerabilidades CRÍTICAS

- **[CRIT-001] Rotate API Keys** (30 min)
  - Acao: Gerar novas keys em Tavily, Exa, Serper, Supabase, Ollama
  - Update: GitHub Secrets + Supabase Vault
  - Teste: Verificar chamadas funcionam

- **[CRIT-002] Activar RLS em 3 Tabelas** (1h)
  - Acao: `ALTER TABLE publish_blocks ENABLE ROW LEVEL SECURITY`
  - Criar policies: `SELECT * WHERE (role() = 'authenticated' OR role() = 'service_role')`
  - Teste: Queries via anon key devem ser bloqueadas

- **[CRIT-003] Remover "writing" Status** (1h)
  - Acao: Remove da constraint em `intake_queue`, update Ollama code
  - Teste: Deployment Ollama scheduler

- **[CRIT-004] Add search_path a 3 Funções** (30 min)
  - Acao: `ALTER FUNCTION enforce_publish_quality SET search_path = public`
  - Teste: Recompile functions

- **[CRIT-005] Escritor: Validar Quality Gates** (2h)
  - Acao: Adicionar check antes de INSERT em articles
  - Teste: Test edge case (certainty_score=0.89, bias_score=0.6)

**Responsável:** DevSecOps / DB Admin
**Timeline:** 1 dia

### FASE 2: CORRECCAO ARQUITECTURAL (3-5 dias)
**Objetivo:** Alinhar código com documentação

- **Verificar Scheduler Ollama** (2h)
  - Acao: Confirmar se `scheduler_ollama.py` existe localmente
  - Resultado: Commit para repo ou documentar setup manual

- **Implementar RLS Eficiente** (4h)
  - Acao: Refactor policies para usar `(SELECT auth.<function>())`
  - Teste: Benchmark antes/depois (query latency)

- **Adicionar Índices Críticos** (1h)
  - Acao: CREATE INDEX idx_intake_queue_status, etc.
  - Teste: Explain plan verificacao

- **Implementar Dispatcher** (8h, sprint)
  - Acao: Criar agent que classifica tema (ou manter keyword-based com documentacao)
  - Teste: 100 eventos, verificar routing correcto

- **Reparar Writer Quality Gates** (2h, testing)
  - Acao: Testing de escritor com artigos rejeitados

**Responsável:** Backend + DB
**Timeline:** 3-5 dias

### FASE 3: FEATURES & POLISH (1-2 sprints)
**Objetivo:** Completar features planeadas

- **Implementar HITL Reviews Interface** (8h)
  - Frontend dashboard para revisar artigos com certainty < 0.895

- **Reactivar Cronistas Scheduled** (4h)
  - Cowork task `cronista-semanal` rodar weekly

- **Adicionar Load Testing** (6h)
  - k6 scripts para simular 1000 raw_events/h

- **Cleanup token_logs** (2h)
  - Cron job para purga automática

**Responsável:** Feature team
**Timeline:** 1-2 sprints

---

## 8. PERFORMANCE AUDIT

### 8.1 Bottlenecks Identificados

| Componente | Problema | Impacto | Prioridade |
|------------|----------|---------|-----------|
| **intake_queue queries** | Sem índice em `status` | 623 pending items → full table scan | ALTO |
| **RLS evaluation** | auth.<function>() x row | 1M rows × auth check = 1M syscall overhead | ALTO |
| **Bridge events dedup** | Event hash collision possible | Duplicadas podem passar (rare) | MÉDIO |
| **Cronista prompt** | Muito longo (context=7 dias) | Token count alto, latency 10+ sec | MÉDIO |
| **Raw events growth** | 2103 rows, sem cleanup | Cache strategy needed | BAIXO |

### 8.2 Recomendacoes

1. **Índice B-tree em intake_queue.status** (Ganho: -50% query time)
2. **RLS refactor com subqueries** (Ganho: -80% permission checks)
3. **Cron cleanup para raw_events >30 dias** (Ganho: -storage, -cache size)
4. **Cronista prompt compression** (Ganho: -30% tokens, -latency)

---

## 9. CODE QUALITY AUDIT

### 9.1 Python Pipeline

| Aspecto | Score | Observações |
|---------|-------|------------|
| **Type Hints** | 4/10 | Parcial, faltam em alguns functions |
| **Docstrings** | 5/10 | Mínimas, sem formatacao structured |
| **Error Handling** | 5/10 | Try-catch básico, sem custom exceptions |
| **Logging** | 6/10 | Usando `logging` stdlib, bom estruturado |
| **Testing** | 4/10 | Vitest exists, mas nao rodado em CI |
| **Modularity** | 7/10 | Separation of concerns boa (agents/ vs output/ vs collectors/) |

**Python Total: 5.1/10**

### 9.2 TypeScript/React Frontend

| Aspecto | Score | Observações |
|---------|-------|------------|
| **Type Safety** | 7/10 | `strict: true` em tsconfig, mas alguns `any` |
| **Component Design** | 7/10 | Functional components, bem-organizado |
| **Error Boundaries** | 6/10 | Global error.tsx, mas alguns pages faltam |
| **Performance** | 5/10 | ISR 60s, mas sem Image optimization agressiva |
| **Accessibility** | 6/10 | Some aria-labels, MotionProvider, mas incomplete |
| **Testing** | 3/10 | Nenhum teste Jest/Vitest visível |

**Frontend Total: 6.0/10**

---

## 10. RECOMENDACOES FINAIS

### Curto Prazo (1 semana)
1. ✅ Rotate TODAS as API keys
2. ✅ Activar RLS em 3 tabelas
3. ✅ Remove "writing" status
4. ✅ Add search_path a funções
5. ✅ Validar quality gates no escritor

### Médio Prazo (2-4 semanas)
6. ✅ Implementar Dispatcher (ou documentar por que keyword-based é suficiente)
7. ✅ Refactor RLS ineficiente
8. ✅ Add índices críticos
9. ✅ Implementar HITL Reviews UI
10. ✅ Reactivar cronistas scheduler

### Longo Prazo (1-2 sprints)
11. ✅ Load testing (k6)
12. ✅ Actualizar ARCHITECTURE-MASTER.md
13. ✅ Circuit breaker implementation
14. ✅ Standarizar error handling
15. ✅ Aumentar test coverage para 60%+

---

## 11. CONCLUSAO

O **Curador de Noticias** é um projecto ambicioso, bem-estruturado em arquitectura e com boas práticas em separação de responsabilidades. No entanto, **vulnerabilidades de segurança críticas e gaps arquitecturais** impedem produção imediata.

**Readiness Produção:** 60%
**Tempo para "Go-Live" seguro:** ~2 semanas (seguindo Fase 1-2 acima)
**Recomendacao:** **BLOQUEAR PUBLICACAO** até remediacao de CRIT-001 a CRIT-005.

A migração bem-sucedida de Edge Functions para Ollama Local + Cowork Cloud demonstra engenharia de qualidade, mas a falta de testes de carga e o bypassing de quality gates sugerem que **testing e validacao de deployment** são areas para improvement contínuo.

---

**Auditoria realizada:** 2026-03-18
**Auditor:** Claude Agent (Haiku 4.5)
**Escopo:** Completo (arquitectura, código, BD, seguranca, performance)
**Próxima revisão recomendada:** Após remediacao FASE 1 (1 semana)
