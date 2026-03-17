# ENGINEER GUIDE — NoticIA
## Manual de Arquitectura e Resolução de Erros

> **Para a equipa técnica (equipa-tecnica Cowork task):**
> Lê este ficheiro na íntegra antes de diagnosticar qualquer problema.
> Este é o manual de verdade — não o ARCHITECTURE-MASTER.md que pode estar desactualizado.

---

## 1. ARQUITECTURA COMPLETA

### 1.1 Visão geral

O NoticIA tem **dois planos de execução** que correm em paralelo:

| Plano | Onde corre | Gere |
|-------|-----------|------|
| **Cowork Cloud** | Servidores Anthropic | Colecta, publicação, monitorização, cronistas |
| **Ollama Local** | Mac do utilizador | Triagem, fact-check, escrita (LLMs pesados) |

Ambos lêem e escrevem na mesma base de dados Supabase (`ljozolszasxppianyaac`).

---

### 1.2 Fluxo completo de um artigo

```
COLECTA (Cowork: collector-orchestrator, cada 20min)
    ↓
intake_queue.status = 'pending'
    ↓
TRIAGEM (Ollama Local: DeepSeek V3.2, cada 20min)
    → classifica área, valida frescura
    → aprovado: status = 'auditor_approved'
    → rejeitado: status = 'auditor_failed'
    ↓
FACT-CHECKER (Ollama Local: Nemotron 3 Super, cada 30min)
    → pesquisa Tavily → Exa → Serper
    → aprovado: status = 'approved'
    → rejeitado: status = 'fact_check'
    ↓
ESCRITOR (Fly.io: nemotron-3-super:cloud, cada 30min)
    → escreve artigo PT-PT
    → insere em articles com status = 'published' DIRECTAMENTE
    → marca intake_queue como status = 'processed'
    ↓
SITE ONLINE (Vercel: noticia-ia.vercel.app)
    ← ISR revalida em 60s após novo artigo
```

---

### 1.3 Cowork Scheduled Tasks (estado actual)

| Task ID | Estado | Intervalo | Função |
|---------|--------|-----------|--------|
| `collector-orchestrator` | ✅ ACTIVO | cada 20min | Chama bridge-events Edge Function |
| `publisher-p2` | ✅ ACTIVO | cada 3h | Publica artigos P2 |
| `publisher-p3` | ✅ ACTIVO | 08h e 20h | Publica artigos P3 |
| `source-finder-cowork` | ✅ ACTIVO | 07h diário | Descobre novos RSS/Telegram |
| `equipa-tecnica` | ✅ ACTIVO | cada 4h | Monitorização e auto-correcção |
| `cronista-semanal` | ✅ ACTIVO | domingo 20h | Gera crónicas dos 10 cronistas |
| `pipeline-triagem` | ⛔ DESACTIVADO | — | MIGRADO para Ollama |
| `agente-fact-checker` | ⛔ DESACTIVADO | — | MIGRADO para Ollama |
| `pipeline-escritor` | ⛔ DESACTIVADO | — | MIGRADO para Ollama |
| `pipeline-orchestrator` | ⛔ DESACTIVADO | — | DEPRECATED |
| `article-processor` | ⛔ DESACTIVADO | — | DEPRECATED — NÃO REACTIVAR |
| `collect-x-cowork` | ⛔ DESACTIVADO | — | Sem API oficial X |
| `pipeline-verificacao` | ⛔ DESACTIVADO | — | DEPRECATED |
| `pipeline-health-check` | ⛔ DESACTIVADO | — | Substituído por equipa-tecnica |

### 1.4 Ollama Local Scheduler (pipeline/src/openclaw/scheduler_ollama.py)

Corre no Mac do utilizador. **Para arrancar:**
```bash
cd pipeline && source .venv/bin/activate && python -m openclaw.scheduler_ollama
```

| Agente | Modelo | Intervalo | Ficheiro |
|--------|--------|-----------|---------|
| Triagem | DeepSeek V3.2 | cada 20min | `agents/triagem.py` |
| Fact-checker | Nemotron 3 Super | cada 30min | `agents/fact_checker.py` |
| Dossiê | Nemotron 3 Super | cada 6h | `agents/dossie.py` |
| Escritor | Nemotron 3 Super | cada 30min | `agents/escritor.py` |

---

### 1.5 Schema da Base de Dados

#### Tabela `intake_queue` — fila de processamento

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | uuid | PK auto |
| `title` | text NOT NULL | Título da notícia |
| `content` | text NOT NULL | Corpo/resumo |
| `url` | text | URL da fonte (**NÃO** `source_url`) |
| `area` | text NOT NULL | portugal/europa/mundo/economia/etc |
| `score` | real NOT NULL | Relevância 0.0–1.0 |
| `status` | text NOT NULL | Ver estados abaixo |
| `priority` | text | p1/p2/p3 |
| `language` | text NOT NULL | 'pt' |
| `metadata` | jsonb | `{source_agent, dossie_id, ...}` |
| `fact_check_summary` | jsonb | Resultado do fact-checker |
| `bias_score` | numeric | 0.0–1.0 |
| `bias_analysis` | jsonb | Análise detalhada |
| `error_message` | text | (**NÃO** `notes`) |
| `received_at` | timestamptz | (**NÃO** `published_at`) |

**Estados válidos de `intake_queue.status`** (constraint `intake_queue_status_check`):
```
pending → auditor_approved → approved → processed
                           ↘ fact_check (rejeitado)
         ↘ auditor_failed (rejeitado pela triagem)
         failed (erro técnico)
         writing (em escrita — não usado actualmente)
         editor_approved / editor_rejected (pipeline antigo — não usar)
```

#### Tabela `articles` — artigos publicados

| Coluna | Tipo | Default | Notas |
|--------|------|---------|-------|
| `id` | uuid | auto | PK |
| `slug` | text NOT NULL | — | URL-friendly |
| `title` | text NOT NULL | — | |
| `body` | text NOT NULL | — | HTML |
| `area` | text NOT NULL | — | |
| `certainty_score` | real NOT NULL | — | Gate: >= 0.895 |
| `status` | text NOT NULL | `'draft'` | |
| `language` | text NOT NULL | `'pt'` | |
| `verification_status` | text NOT NULL | `'none'` | |
| `bias_score` | numeric | — | Gate: <= 0.5 |
| `created_at` | timestamptz | `now()` | auto |
| `updated_at` | timestamptz | `now()` | auto |

**Trigger de qualidade** (`enforce_publish_quality`):
```sql
-- Bloqueia publicação se:
certainty_score < 0.895  -- (não 0.9 — precisão float64)
bias_score > 0.5
```

---

### 1.6 Edge Functions Supabase (supabase/functions/)

| Função | Estado | Usado por |
|--------|--------|----------|
| `bridge-events` | ✅ ACTIVA | collector-orchestrator |
| `collect-rss` | ✅ ACTIVA | collector-orchestrator |
| `source-finder` | ✅ ACTIVA | source-finder-cowork |
| `agent-log` | ✅ ACTIVA | equipa-tecnica (logging) |
| `receive-article` | ✅ ACTIVA | publisher tasks |
| `cronista` | ✅ ACTIVA | cronista-semanal |
| `article-card` | ⚠️ Verificar | Possivelmente obsoleta |
| `publish-instagram` | ⚠️ Verificar | Não há task activa |
| `collect-x-grok` | ⛔ OBSOLETA | collect-x desactivado |
| `grok-bias-check` | ⛔ OBSOLETA | Substituído por Ollama |
| `grok-fact-check` | ⛔ OBSOLETA | Substituído por Ollama |
| `receive-claims` | ⛔ OBSOLETA | Pipeline antigo |
| `receive-rationale` | ⛔ OBSOLETA | Pipeline antigo |
| `writer-publisher` | ⛔ OBSOLETA | Substituído por Ollama escritor |

---

### 1.7 Variáveis de Ambiente críticas

**`pipeline/.env`** (Python local):
```env
SUPABASE_URL=https://ljozolszasxppianyaac.supabase.co
SUPABASE_SERVICE_KEY=...
OLLAMA_API_KEY=...
OLLAMA_BASE_URL=https://ollama.com   # → /v1 é adicionado pelo cliente
MODEL_TRIAGEM=deepseek-v3.2:cloud
MODEL_FACTCHECKER=nemotron-3-super:cloud
MODEL_DOSSIE=nemotron-3-super:cloud
MODEL_ESCRITOR=nemotron-3-super:cloud
TAVILY_API_KEY=tvly-dev-...          # primário
EXA_API_KEY=...                      # fallback
SERPER_API_KEY=...                   # último recurso (viés Google)
```

**`.env.local`** (Next.js frontend — raiz do projecto):
```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

---

## 2. DIAGNÓSTICO RÁPIDO

### 2.1 Checklist de saúde (correr a cada verificação)

```sql
-- Estado do pipeline
SELECT status, count(*) FROM intake_queue GROUP BY status ORDER BY count DESC;

-- Últimos artigos publicados
SELECT title, certainty_score, bias_score, created_at
FROM articles WHERE status = 'published'
ORDER BY created_at DESC LIMIT 5;

-- Artigos prontos para publicar
SELECT count(*) FROM articles WHERE status = 'processed';

-- Constraint activa
SELECT pg_get_constraintdef(oid) FROM pg_constraint
WHERE conname = 'intake_queue_status_check';
```

### 2.2 Interpretação dos resultados

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| 0 itens `pending` há horas | Collector parou ou sem fontes | Verificar collector-orchestrator Cowork task |
| Items stuck em `auditor_approved` > 1h | Ollama scheduler parou no Mac | Reiniciar `python -m openclaw.scheduler_ollama` |
| Items stuck em `approved` > 1h | Ollama scheduler parou | Idem |
| `fact_check` a crescer muito | Threshold 0.895 muito alto, ou LLM com baixa confiança | Verificar prompts do fact-checker |
| 0 itens `processed` em `articles` | Escritor não correu ou publisher não publicou | Verificar scheduler + publisher-p2/p3 Cowork |
| Erro de constraint na DB | Status inválido no código | Ver secção 3.1 |
| Artigos duplicados | Dedup por URL falhou | Verificar campo `url` no insert |

---

## 3. ERROS COMUNS E SOLUÇÕES

### 3.1 `violates check constraint "intake_queue_status_check"`

**Causa:** Código a tentar escrever um status não permitido na `intake_queue`.

**Estados permitidos actualmente:**
`pending, auditor_approved, auditor_failed, approved, fact_check, writing, processed, failed, editor_approved, editor_rejected`

**Diagnóstico:**
```sql
SELECT pg_get_constraintdef(oid) FROM pg_constraint
WHERE conname = 'intake_queue_status_check';
```

**Solução — adicionar novo status:**
```sql
ALTER TABLE intake_queue DROP CONSTRAINT intake_queue_status_check;
ALTER TABLE intake_queue ADD CONSTRAINT intake_queue_status_check
  CHECK (status = ANY (ARRAY[
    'pending', 'auditor_approved', 'auditor_failed',
    'approved', 'fact_check', 'writing', 'processed', 'failed',
    'editor_approved', 'editor_rejected'
    -- adicionar novo status aqui
  ]));
```

**⚠️ ATENÇÃO:** Este erro falha silenciosamente no Python local (exception capturada pelo try/except). Os itens ficam stuck no status anterior sem mensagem de erro visível no Supabase.

---

### 3.2 Items stuck em `auditor_approved` sem avançar

**Causa mais comum:** Scheduler Ollama parou no Mac do utilizador.

**Diagnóstico:**
```sql
SELECT id, title, status, received_at
FROM intake_queue
WHERE status = 'auditor_approved'
ORDER BY received_at ASC LIMIT 5;
```
Se `received_at` > 1 hora, o scheduler está parado.

**Solução:**
```bash
cd pipeline && source .venv/bin/activate && python -m openclaw.scheduler_ollama
```

---

### 3.3 Items em `editor_approved` (status antigo)

**Causa:** Pipeline antigo (Cowork) usava `editor_approved`. O novo escritor Ollama lê `approved`.

**Solução imediata:**
```sql
UPDATE intake_queue SET status = 'approved' WHERE status = 'editor_approved';
```

---

### 3.4 Artigos não publicam apesar de estarem `processed`

**Causa:** Publisher Cowork (publisher-p2 ou publisher-p3) não correu ou tem erro.

**Diagnóstico:**
```sql
SELECT id, title, certainty_score, bias_score, created_at
FROM articles WHERE status = 'processed'
ORDER BY created_at DESC;
```

**Verificar publisher:**
- No Cowork, confirmar que `publisher-p2` e `publisher-p3` estão enabled
- Ver `lastRunAt` — se > 4h, há problema

**Causa alternativa — trigger a bloquear:**
```sql
-- Ver se o trigger está activo
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_table = 'articles'
AND trigger_name = 'enforce_publish_quality_gate';
```

---

### 3.5 `MIDDLEWARE_INVOCATION_FAILED` no Vercel

**Causa:** Variáveis de ambiente Supabase em falta no `.env.local` ou no Vercel dashboard.

**Solução:**
- Confirmar que `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY` estão no Vercel → Settings → Environment Variables
- O ficheiro `src/lib/supabase/middleware.ts` tem null-check — se as vars estiverem em falta, retorna early em vez de crashar

---

### 3.6 `500 error` nas páginas de artigos individuais

**Causa original (resolvida):** `isomorphic-dompurify` usava `jsdom` que falha em Vercel serverless.

**Solução aplicada:** `src/lib/utils/sanitize-html.ts` foi reescrito com regex puro (sem dependências).

**Se voltar a aparecer:** Confirmar que não foi feita uma nova dependência que use jsdom.

---

### 3.7 Fact-checker sem pesquisa real (logs: "Nenhum provider disponível")

**Causa:** Keys de pesquisa em falta no `pipeline/.env`.

**Diagnóstico:**
```bash
grep -E "TAVILY|EXA|SERPER" pipeline/.env
```

**Solução:** As 3 keys devem estar em `pipeline/.env` (não `.env.local`):
```env
TAVILY_API_KEY=tvly-dev-...
EXA_API_KEY=...
SERPER_API_KEY=...
```

**Fallback automático:** Tavily → Exa → Serper. Se Tavily falhar, tenta Exa automaticamente.

---

### 3.8 Ollama API não responde

**Diagnóstico:**
```python
from openai import OpenAI
client = OpenAI(base_url="https://ollama.com/v1", api_key="OLLAMA_API_KEY")
r = client.chat.completions.create(
    model="deepseek-v3.2:cloud",
    messages=[{"role": "user", "content": "OK?"}],
    max_tokens=5
)
print(r.choices[0].message.content)
```

**Causas comuns:**
- Key expirada → renovar em ollama.com
- Modelo não disponível → verificar em ollama.com/models
- Rate limit → aguardar ou reduzir `BATCH_SIZE` em `.env`

---

### 3.9 Git index.lock (impossível fazer commit)

**Causa:** Lock file no `.git/index.lock` — Mac não deixa apagar directamente por permissões.

**Solução:**
```bash
rm '/path/to/Curador de noticias/.git/index.lock'
```
Se der "Operation not permitted", usar:
```bash
cp -r '/path/to/Curador de noticias/.git' /tmp/noticia-git-tmp
rm /tmp/noticia-git-tmp/index.lock
GIT_DIR=/tmp/noticia-git-tmp git -C '/path/to/Curador de noticias' status
```

### 3.10 `violates check constraint "articles_status_check"`

**Causa:** A constraint da tabela `articles` não inclui `processed` — apenas: `draft`, `review`, `published`, `rejected`, `archived`, `fact_check`. O escritor tentava inserir artigos com `status='processed'`.

**Sintomas:**
- Artigos em `intake_queue` com `status='approved'` ficam presos
- Logs do escritor: `new row for relation "articles" violates check constraint "articles_status_check"`
- Artigos nunca aparecem no site apesar do escritor correr

**Solução aplicada (2026-03-17):** O `escritor.py` foi alterado para publicar directamente com `status='published'` (em vez de `processed`). Não adicionar `processed` à constraint — não é necessário.

**Verificar:**
```sql
SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'articles_status_check';
-- Deve conter: 'published' mas NÃO 'processed'
```

**Se o erro reaparecer:** Verificar que `escritor.py` linha `_publicar_artigo()` tem `"status": "published"` e NÃO `"status": "processed"`.

---

### 3.11 Modelo Ollama Cloud retorna 404

**Causa:** Um modelo LLM foi removido ou renomeado na plataforma Ollama Cloud. Modelos cloud têm tags específicas que podem mudar.

**Sintomas:**
- Logs: `404 Not Found` ou `model not found`
- Agente falha silenciosamente, items ficam stuck no status anterior
- Pipeline corre mas não avança

**Modelos actuais (verificados 2026-03-17):**
| Agente | Variável | Modelo |
|--------|----------|--------|
| Triagem | `MODEL_TRIAGEM` | `deepseek-v3:cloud` |
| Fact-checker | `MODEL_FACT_CHECKER` | `nemotron-3-super:cloud` |
| Dossier | `MODEL_DOSSIE` | `nemotron-3-super:cloud` |
| Escritor | `MODEL_ESCRITOR` | `nemotron-3-super:cloud` |

**Solução:** Verificar modelos disponíveis em https://ollama.com/library?q=&capability=tools — usar a tag `:cloud` para modelos hosted. Actualizar `.env` no pipeline e secrets no Fly.io:
```bash
fly secrets set MODEL_ESCRITOR="nome-correcto:cloud" --app noticia-scheduler
```

---

## 4. MÓDULOS ACTIVOS vs OBSOLETOS

### 4.1 Pipeline Python — o que usar

| Módulo | Estado | Usar? |
|--------|--------|-------|
| `agents/ollama_client.py` | ✅ ACTIVO | Sim — cliente base para todos os agentes |
| `agents/triagem.py` | ✅ ACTIVO | Sim |
| `agents/fact_checker.py` | ✅ ACTIVO | Sim |
| `agents/dossie.py` | ✅ ACTIVO | Sim |
| `agents/escritor.py` | ✅ ACTIVO | Sim |
| `scheduler_ollama.py` | ✅ ACTIVO | Sim — ponto de entrada |
| `collectors/` | ✅ ACTIVO | Usado pelo Cowork via bridge.py |
| `output/supabase_intake.py` | ✅ ACTIVO | Usado pelos collectors |
| `editorial/` | ⛔ OBSOLETO | Era Grok — substituído por Ollama |
| `factcheck/` | ⛔ OBSOLETO | Era keyword-based — substituído por Ollama |
| `reporters/` | ⛔ OBSOLETO | Era pipeline antigo |
| `curador/` | ⛔ OBSOLETO | Era pipeline antigo |
| `scheduler/runner.py` | ⛔ OBSOLETO | Substituído por scheduler_ollama.py |

### 4.2 Ficheiros .md na raiz — o que é activo

| Ficheiro | Estado | Usar? |
|----------|--------|-------|
| `CLAUDE.md` | ✅ ACTIVO | Sempre — instrução base |
| `ARCHITECTURE-MASTER.md` | ✅ ACTIVO | Referência (pode estar desactualizado) |
| `ENGINEER-GUIDE.md` | ✅ ACTIVO | Este ficheiro — fonte de verdade operacional |
| `AGENT-PROFILES.md` | ✅ ACTIVO | Personalidades dos cronistas |
| `COWORK-EQUIPA-TECNICA.md` | ✅ ACTIVO | Prompt do task equipa-tecnica |
| `COWORK-SOURCE-FINDER.md` | ✅ ACTIVO | Prompt do task source-finder |
| `ANALYTICS-PRIVACY-PROMPT.md` | ⏳ PENDENTE | Para Claude Code — analytics + privacidade |
| `HETERONIMOS-PROMPTS.md` | ✅ ACTIVO | Para os cronistas |
| `archive/` | ⛔ OBSOLETO | Não usar como referência |
| `OLLAMA-MIGRATION-PROMPT.md` | ⛔ EXECUTADO | Migração já concluída |
| `SEARCH-FIX-PROMPT.md` | ⛔ EXECUTADO | Fix já concluído |
| `ENV-FIX-PROMPT.md` | ⛔ EXECUTADO | Fix já concluído |
| `FIX-PROMPT.md` | ⛔ EXECUTADO | Fix já concluído |
| `AUDIT-PROMPT.md` | ⛔ EXECUTADO | Auditoria já concluída |
| `COWORK-PIPELINE-TRIAGEM.md` | ⛔ OBSOLETO | Migrado para Ollama |
| `COWORK-PIPELINE-ESCRITOR.md` | ⛔ OBSOLETO | Migrado para Ollama |

---

## 5. MONITORIZAÇÃO PROACTIVA (para equipa-tecnica)

A `equipa-tecnica` deve correr estas verificações a cada ciclo (4h):

### 5.1 Verificar pipeline stuck

```sql
-- Items em auditor_approved há mais de 1h (scheduler pode estar parado)
SELECT count(*) as stuck
FROM intake_queue
WHERE status = 'auditor_approved'
AND received_at < now() - interval '1 hour';

-- Items em approved há mais de 1h (escritor pode estar parado)
SELECT count(*) as stuck
FROM intake_queue
WHERE status = 'approved'
AND received_at < now() - interval '1 hour';
```

Se `stuck > 0`: **o scheduler Ollama local parou.** Notificar o utilizador imediatamente.

### 5.2 Verificar qualidade dos artigos

```sql
-- Taxa de rejeição do fact-checker (deve ser < 40%)
SELECT
  round(count(*) FILTER (WHERE status = 'fact_check') * 100.0 / count(*), 1) as rejection_rate
FROM intake_queue
WHERE status IN ('approved', 'fact_check')
AND received_at > now() - interval '24 hours';
```

### 5.3 Auto-correcção de items com status antigo

```sql
-- Corrigir editor_approved automaticamente
UPDATE intake_queue SET status = 'approved'
WHERE status = 'editor_approved';
```

### 5.4 Verificar constraint da DB (executar 1x/dia)

```sql
SELECT pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'intake_queue_status_check';
```
Confirmar que inclui: `'approved'` e `'fact_check'` na lista.

---

## 6. DEPLOY E INFRAESTRUTURA

| Componente | Plataforma | URL | Deploy |
|-----------|-----------|-----|--------|
| Frontend | Vercel | noticia-ia.vercel.app | Auto via git push |
| Base de dados | Supabase | ljozolszasxppianyaac | Migrations manuais |
| Edge Functions | Supabase | supabase.co/functions | `supabase functions deploy` |
| Pipeline Ollama | Mac local | — | Manual: `python -m openclaw.scheduler_ollama` |
| LLMs | Ollama Cloud | ollama.com/api/v1 | API key em pipeline/.env |

### Stack técnico

- **Frontend:** Next.js 15, TypeScript strict, Tailwind CSS
- **Pipeline:** Python 3.14, APScheduler, python-dotenv
- **DB:** PostgreSQL (Supabase), triggers PL/pgSQL
- **LLMs:** DeepSeek V3.2 (triagem), Nemotron 3 Super (fact-check + dossiê + escrita)
- **Search:** Tavily → Exa.ai → Serper.dev (cascata)
- **Git:** github.com/WilsonArim/NoticIA

---

*Última actualização: Março 2026*
*Manter actualizado sempre que houver mudanças de arquitectura.*
