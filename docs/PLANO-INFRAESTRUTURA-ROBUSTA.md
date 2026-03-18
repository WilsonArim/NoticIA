# Plano de Implementação — Infraestrutura Robusta

> Baseado na pesquisa do LMNotebook (2026-03-18) e na auditoria completa do sistema.
> Cada fase é auto-contida e executável numa sessão de trabalho independente.

---

## Resumo Executivo

| Fase | Prazo | Items | Objectivo |
|------|-------|-------|-----------|
| **P1** | Esta semana (18-24 Mar) | 6 items | Eliminar falhas silenciosas — nunca mais perder artigos sem saber |
| **P2** | Este mês (25 Mar - 15 Abr) | 6 items | Automatizar qualidade — testes, CI/CD, observabilidade |
| **P3** | Próximo trimestre (Abr-Jun) | 4 items | Escalar — multi-idioma, separação de serviços, evals semânticos |

---

## FASE P1 — Eliminar Falhas Silenciosas (Esta Semana)

### P1.1 — Stored Procedure Atómica `publish_article_with_sources`

**Problema:** 6 inserts separados (article → source → claim → article_claims → claim_sources → update intake_queue). Se 1 falha = artigo sem fontes.

**Solução:** Uma única função PL/pgSQL no Supabase que faz tudo numa transação atómica.

**Implementação:**
```sql
CREATE OR REPLACE FUNCTION publish_article_with_sources(payload JSONB)
RETURNS JSON AS $$
DECLARE
  new_article_id UUID;
  new_claim_id UUID;
  source_id UUID;
  fonte TEXT;
BEGIN
  -- 1. Inserir artigo
  INSERT INTO articles (title, subtitle, slug, lead, body, body_html, area, priority,
    certainty_score, bias_score, status, tags, language, verification_status)
  VALUES (
    payload->>'title', payload->>'subtitle', payload->>'slug',
    payload->>'lead', payload->>'body', payload->>'body_html',
    payload->>'area', payload->>'priority',
    (payload->>'certainty_score')::float, (payload->>'bias_score')::float,
    'published', ARRAY(SELECT jsonb_array_elements_text(payload->'tags')),
    'pt', 'none'
  ) RETURNING id INTO new_article_id;

  -- 2. Inserir claim principal
  INSERT INTO claims (original_text, subject, predicate, object, verification_status, confidence_score)
  VALUES (
    payload->>'claim_text', payload->>'claim_subject',
    'verificado por', 'múltiplas fontes', 'verified',
    (payload->>'certainty_score')::float
  ) RETURNING id INTO new_claim_id;

  -- 3. Ligar claim ao artigo
  INSERT INTO article_claims (article_id, claim_id, position) VALUES (new_article_id, new_claim_id, 0);

  -- 4. Inserir fontes e ligar ao claim
  FOR fonte IN SELECT jsonb_array_elements_text(payload->'fontes')
  LOOP
    -- Upsert source (reutiliza se já existir)
    INSERT INTO sources (url, domain, title, content_hash, source_type, reliability_score, metadata)
    VALUES (fonte, split_part(fonte, '/', 3), split_part(fonte, '/', 3),
            md5(fonte), 'web', 0.75, '{"via": "fact_checker"}'::jsonb)
    ON CONFLICT (content_hash) DO UPDATE SET url = EXCLUDED.url
    RETURNING id INTO source_id;

    INSERT INTO claim_sources (claim_id, source_id, supports) VALUES (new_claim_id, source_id, true);
  END LOOP;

  -- 5. Marcar intake_queue como processado
  UPDATE intake_queue SET status = 'processed'
  WHERE id = (payload->>'intake_queue_id')::uuid;

  RETURN json_build_object('article_id', new_article_id, 'claim_id', new_claim_id, 'success', true);

EXCEPTION WHEN OTHERS THEN
  RAISE;  -- Rollback automático de tudo
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
```

**No escritor.py:** Substituir os 6 inserts por:
```python
result = supabase.rpc('publish_article_with_sources', {
    'title': artigo['titulo'], 'slug': slug, ...
    'fontes': todas_fontes, 'intake_queue_id': item['id']
}).execute()
```

**Verificação:** Publicar 1 artigo → confirmar que `articles`, `claims`, `article_claims`, `claim_sources` e `sources` têm dados + `intake_queue` marcado como `processed`.

**Referências:** Supabase RPC docs, PL/pgSQL transaction guarantees.

---

### P1.2 — Heartbeats com Better Stack

**Problema:** Se o Fly.io crashar, ninguém sabe durante horas.

**Solução:** Better Stack (free tier: 10 monitors, 3min check interval).

**Implementação:**
1. Criar conta grátis em betterstack.com
2. Criar 4 heartbeat monitors:
   - `noticia-rss-collector` (esperado cada 15min, grace 5min)
   - `noticia-triagem` (esperado cada 20min, grace 10min)
   - `noticia-escritor` (esperado cada 30min, grace 15min)
   - `noticia-telegram` (esperado cada 5min, grace 10min)
3. Configurar alerta Telegram (Better Stack → Telegram webhook)
4. No final de cada agente, adicionar:
```python
import httpx
HEARTBEAT_URL = os.getenv("HEARTBEAT_URL_TRIAGEM", "")
def send_heartbeat():
    if HEARTBEAT_URL:
        try:
            httpx.get(HEARTBEAT_URL, timeout=5)
        except Exception:
            pass  # Heartbeat failure should never crash the agent
```

**Verificação:** Parar o Fly.io manualmente → receber alerta no Telegram em <5min.

**Custo:** Grátis (free tier).

---

### P1.3 — Circuit Breaker Real (Tenacity + PyBreaker)

**Problema:** Se Ollama Cloud cair, o pipeline tenta infinitamente sem alerta.

**Solução:** Circuit breaker que abre após 3 falhas, pausa 5min, alerta via Telegram.

**Implementação:**
1. Adicionar ao `requirements-scheduler.txt`:
```
tenacity>=8.0
pybreaker>=1.0
```

2. Criar `pipeline/src/openclaw/agents/resilience.py`:
```python
import os, logging, pybreaker
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)

HEARTBEAT_ALERT_URL = os.getenv("HEARTBEAT_ALERT_URL", "")

def _on_circuit_open(breaker, error):
    logger.critical("CIRCUIT OPEN: %s — %s", breaker.name, error)
    if HEARTBEAT_ALERT_URL:
        import httpx
        try:
            httpx.post(HEARTBEAT_ALERT_URL, json={"text": f"🔴 CIRCUIT OPEN: {breaker.name}"}, timeout=5)
        except Exception:
            pass

ollama_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=300, name="ollama",
    listeners=[pybreaker.CircuitBreakerListener()]
)
ollama_breaker._state_storage._on_open = lambda: _on_circuit_open(ollama_breaker, "Ollama Cloud")

tavily_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=120, name="tavily")

@retry(wait=wait_exponential(multiplier=1, min=4, max=60), stop=stop_after_attempt(3),
       retry=retry_if_exception_type((ConnectionError, TimeoutError)))
def call_ollama_with_retry(client, **kwargs):
    return ollama_breaker.call(client.chat.completions.create, **kwargs)
```

3. No `ollama_client.py`, substituir `client.chat.completions.create(**kwargs)` por `call_ollama_with_retry(client, **kwargs)`.

**Verificação:** Simular timeout do Ollama (URL inválido) → circuit abre após 3 falhas → alerta Telegram.

**Custo:** Grátis (open source).

---

### P1.4 — Alertas Isolados via pg_cron + Telegram

**Problema:** Se TODO o Python morrer, ninguém alerta. A monitorização actual depende do mesmo sistema que pode falhar.

**Solução:** Alerta directo do Postgres (pg_cron + pg_net) → Telegram. Independente de Python/Fly.io.

**Implementação:**
1. Criar Edge Function `alert-telegram`:
```typescript
Deno.serve(async (req) => {
  const { message } = await req.json();
  const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
  const CHAT_ID = Deno.env.get("TELEGRAM_ALERT_CHAT_ID")!;
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ chat_id: CHAT_ID, text: message, parse_mode: "Markdown" })
  });
  return new Response("ok");
});
```

2. pg_cron job cada 30min:
```sql
SELECT cron.schedule('alert-no-articles', '*/30 * * * *', $$
  DO $body$
  DECLARE
    horas_sem_artigo FLOAT;
  BEGIN
    SELECT EXTRACT(EPOCH FROM (now() - max(created_at)))/3600
    INTO horas_sem_artigo FROM articles WHERE status = 'published';

    IF horas_sem_artigo > 6 THEN
      PERFORM net.http_post(
        url := current_setting('app.supabase_url') || '/functions/v1/alert-telegram',
        headers := json_build_object('Authorization', 'Bearer ' || current_setting('app.publish_api_key'))::jsonb,
        body := json_build_object('message', '🔴 ALERTA: ' || round(horas_sem_artigo::numeric,1) || 'h sem artigos novos!')::jsonb
      );
    END IF;
  END $body$;
$$);
```

**Verificação:** Não publicar artigos durante 6h → receber alerta Telegram.

**Custo:** Grátis (Supabase Edge Function + pg_cron).

---

### P1.5 — Gitleaks Pre-commit Hook

**Problema:** API keys foram commitadas no git (CRIT-001 da auditoria).

**Solução:** Hook que bloqueia commits com secrets.

**Implementação:**
```bash
# Instalar
brew install gitleaks  # ou pip install pre-commit

# Criar .pre-commit-config.yaml na raiz:
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks

# Activar
pre-commit install
```

**Verificação:** Tentar commit de ficheiro com `API_KEY=sk-...` → bloqueado.

**Custo:** Grátis.

---

### P1.6 — Idempotência com ON CONFLICT

**Problema:** Retries podem publicar artigos duplicados.

**Solução:** Constraints únicas + `ON CONFLICT DO NOTHING` em todos os inserts.

**Implementação:**
```sql
-- Garantir unicidade no slug (já existe como padrão)
ALTER TABLE articles ADD CONSTRAINT IF NOT EXISTS articles_slug_unique UNIQUE (slug);

-- A stored procedure P1.1 já usa ON CONFLICT para sources
-- Verificar intake_queue dedup:
ALTER TABLE intake_queue ADD CONSTRAINT IF NOT EXISTS intake_queue_url_unique UNIQUE (url);
```

No escritor e fact-checker, todos os inserts devem usar `ON CONFLICT DO NOTHING` ou `ON CONFLICT DO UPDATE`.

**Verificação:** Tentar inserir artigo com slug duplicado → sem erro, sem duplicado.

**Custo:** Grátis.

---

## FASE P2 — Automatizar Qualidade (Este Mês)

### P2.1 — Procrastinate (Queue PostgreSQL) em vez de APScheduler

**Problema:** APScheduler perde estado entre deploys, misfire_grace_time causa jobs perdidos.

**Solução:** Procrastinate usa o PostgreSQL como broker — jobs sobrevivem a crashes.

**Implementação:**
1. Adicionar `procrastinate>=3.0` ao `requirements-scheduler.txt`
2. Reescrever `scheduler_ollama.py`:
```python
import procrastinate

app = procrastinate.App(
    connector=procrastinate.SyncPsycopgConnector(
        host=SUPABASE_HOST, port=5432, dbname="postgres",
        user="postgres", password=SUPABASE_DB_PASSWORD
    )
)

@app.task(queue="pipeline")
def task_triagem():
    run_triagem()

@app.task(queue="pipeline")
def task_fact_checker():
    run_fact_checker()

@app.task(queue="pipeline")
def task_escritor():
    run_escritor()

# Agendar periodicamente
@app.periodic(cron="*/20 * * * *")
def schedule_triagem(timestamp):
    task_triagem.defer()

@app.periodic(cron="*/25 * * * *")
def schedule_fact_checker(timestamp):
    task_fact_checker.defer()

@app.periodic(cron="*/30 * * * *")
def schedule_escritor(timestamp):
    task_escritor.defer()
```
3. Executar as migrações do Procrastinate no Supabase (cria tabelas internas).

**Verificação:** Crashar o Fly.io → reiniciar → jobs pendentes são retomados automaticamente.

**Custo:** Grátis (open source). Requer acesso directo ao PostgreSQL (connection string do Supabase).

**Referências:** Procrastinate quickstart, psycopg3 connection pools.

---

### P2.2 — CI/CD Completo no GitHub Actions

**Problema:** Erros (regex inválido, imports errados) chegam a produção. Sem rollback automático.

**Solução:** Pipeline de 4 stages: lint → test → deploy → smoke test + rollback.

**Implementação:** Actualizar `.github/workflows/deploy-scheduler.yml`:
```yaml
name: Deploy Scheduler to Fly.io
on:
  push:
    branches: [main]
    paths: ["pipeline/**"]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r pipeline/requirements-scheduler.txt
      - run: cd pipeline && python -m flake8 src/ --max-line-length 120
      - run: cd pipeline && python -m pytest tests/ -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        working-directory: pipeline
        env: { FLY_API_TOKEN: "${{ secrets.FLY_API_TOKEN }}" }

      # Smoke test: wait 60s, check if scheduler is alive
      - run: sleep 60
      - run: |
          STATUS=$(flyctl status --app noticia-scheduler --json | jq -r '.Machines[0].state')
          if [ "$STATUS" != "started" ]; then
            echo "Deploy failed — rolling back"
            flyctl releases rollback --app noticia-scheduler
            exit 1
          fi
        env: { FLY_API_TOKEN: "${{ secrets.FLY_API_TOKEN }}" }
```

**Verificação:** Push código com import errado → CI falha → deploy não acontece.

**Custo:** Grátis (GitHub Actions free tier).

---

### P2.3 — Testes com Mock LLM (pytest-mockllm)

**Problema:** Sem testes, erros só são descobertos em produção.

**Solução:** Mock das chamadas LLM para testar status transitions sem gastar tokens.

**Implementação:**
```python
# tests/test_escritor.py
import json
from unittest.mock import patch, MagicMock

def test_escritor_publishes_article():
    """Test that escritor creates article from approved item."""
    mock_response = json.dumps({
        "titulo": "Teste Artigo",
        "subtitulo": "Subtítulo",
        "lead": "Lead do artigo.",
        "corpo_html": "<p>Corpo</p>",
        "tags": ["teste"],
        "slug": "teste-artigo"
    })

    with patch('openclaw.agents.ollama_client.chat', return_value=mock_response):
        with patch('openclaw.agents.escritor.create_client') as mock_sb:
            mock_table = MagicMock()
            mock_sb.return_value.table.return_value = mock_table
            mock_sb.return_value.rpc.return_value.execute.return_value = MagicMock(
                data={'article_id': 'test-uuid', 'success': True}
            )

            from openclaw.agents.escritor import run_escritor
            # Assert no exceptions, article created
```

**Verificação:** `pytest tests/ -v` passa sem chamadas reais a APIs.

**Custo:** Grátis.

---

### P2.4 — Trace IDs End-to-End

**Problema:** Impossível seguir uma notícia desde raw_event até artigo publicado.

**Solução:** Gerar UUID na coleta, propagar por todas as stages.

**Implementação:**
1. Coluna `trace_id` na `raw_events` (gerada pelo coletor como hash do URL).
2. Propagar para `intake_queue.metadata.trace_id`.
3. Propagar para `articles.metadata.trace_id`.
4. Em cada agente, logar com o trace_id:
```python
import json_logging
logger.info("Triagem", extra={"trace_id": item["metadata"].get("trace_id"), "stage": "triagem", "status": "approved"})
```

**Verificação:** Dado um artigo publicado, conseguir reconstruir o percurso completo com:
```sql
SELECT * FROM raw_events WHERE event_hash = '<trace_id>';
SELECT * FROM intake_queue WHERE metadata->>'trace_id' = '<trace_id>';
SELECT * FROM articles WHERE metadata->>'trace_id' = '<trace_id>';
```

**Custo:** Grátis.

---

### P2.5 — Infisical para Secrets Unificados

**Problema:** Secrets dispersos entre .env local, Fly.io secrets, Supabase vault.

**Solução:** Infisical (free tier) como fonte única de verdade.

**Implementação:**
1. Criar projecto no infisical.com com 3 ambientes: dev, staging, prod.
2. Importar todos os secrets actuais.
3. No Fly.io: `infisical run --env=prod -- python -m openclaw.scheduler_ollama`
4. No local: `infisical run --env=dev -- python -m openclaw.scheduler_ollama`
5. Apagar `.env` locais (manter `.env.example` com placeholders).

**Verificação:** Rodar key → actualizar em Infisical → Fly.io apanha nova key sem redeploy.

**Custo:** Grátis (hobby tier).

---

### P2.6 — Supabase Sentinel para Auditoria RLS Automática

**Problema:** RLS pode ter gaps que só se descobrem em auditorias manuais.

**Solução:** Integrar verificação RLS no CI/CD.

**Implementação:**
```yaml
# No GitHub Actions, após deploy:
- name: RLS Audit
  run: |
    npx supabase-sentinel audit --project-id ljozolszasxppianyaac
  env:
    SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
```

Alternativa simples sem ferramenta externa:
```sql
-- Query para encontrar tabelas públicas sem RLS
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT IN (SELECT tablename FROM pg_tables WHERE rowsecurity = true);
```

**Verificação:** Criar tabela sem RLS → CI falha.

**Custo:** Grátis.

---

## FASE P3 — Escalar (Próximo Trimestre)

### P3.1 — Separar Collectors e Workers em Containers

**Problema:** Um crash no collector afecta o escritor (mesmo Fly.io app).

**Solução:** 3 apps independentes:
- `noticia-collectors` (RSS + bridge)
- `noticia-workers` (triagem + fact-check + escritor)
- `noticia-telegram` (já separado)

**Custo:** ~$5/mês por app extra no Fly.io.

---

### P3.2 — RunPod Serverless para Modelos Locais

**Problema:** Se custos Ollama Cloud ultrapassarem ~$30-50/mês.

**Solução:** RunPod Serverless com A100 (~$0.60/hora, cobrado ao segundo).

**Trigger:** Monitorizar custos mensais. Se >$50, migrar modelos pesados.

---

### P3.3 — Multi-idioma com JSONB

**Problema:** Expandir de PT-PT para EN, ES, FR.

**Solução:** Converter `title` e `body` para JSONB: `{"pt": "Título", "en": "Title"}`.

**Implementação:**
```sql
ALTER TABLE articles ALTER COLUMN title TYPE JSONB USING jsonb_build_object('pt', title);
ALTER TABLE articles ALTER COLUMN body TYPE JSONB USING jsonb_build_object('pt', body);
```

---

### P3.4 — Evals Semânticos com Promptfoo

**Problema:** Alterações ao prompt do escritor podem degradar qualidade.

**Solução:** `npx promptfoo eval` no CI — LLM-as-a-judge verifica se títulos são factuais.

**Custo:** Grátis (open source, custos de tokens para o judge).

---

### P3.5 — Paperclip: Orquestração Profissional dos Agentes

**Problema:** Os ~45 agentes do NoticIA estão orquestrados por uma manta de retalhos — pg_cron para coletores, APScheduler/Procrastinate para LLMs, Cowork tasks para publishers. Sem visão unificada, sem org chart, sem governance real.

**Solução:** [Paperclip](https://paperclip.ing/) — plataforma open-source (MIT) de orquestração de agentes como empresa. Node.js + React + PostgreSQL.

**Fonte:** [GitHub](https://github.com/paperclipai/paperclip) (4.3k+ stars, lançado Mar 2026)

**O que é:** "If OpenClaw is an _employee_, Paperclip is the _company_." — Uma camada de gestão que trata agentes como funcionários com org chart, budgets, heartbeats, governance e audit trails.

**Porque encaixa no NoticIA:**

| Feature Paperclip | Problema NoticIA que resolve |
|-------------------|------------------------------|
| **Org chart com hierarquia** | Escritor reporta ao Editor-Chefe, Reporters ao Dispatcher — definido na arquitectura mas nunca implementado como sistema |
| **Heartbeat scheduling** | Substitui APScheduler/Procrastinate — agentes acordam, verificam trabalho, executam, reportam |
| **Budget enforcement** | Controlo de custos por agente (Nemotron, DeepSeek, Tavily) — token_logs existe mas não controla |
| **Atomic task checkout** | Sem duplicate work — resolve jobs saltados pelo APScheduler |
| **Governance (HITL)** | Tu aprovas decisões, pausas agentes, vês dashboard — o HITL que está em falta |
| **Audit trails** | Tracing completo de cada decisão — resolve P2.4 (trace IDs) automaticamente |
| **Multi-company isolation** | Futuro: NoticIA PT + NoticIA EN + NoticIA ES como "empresas" isoladas |
| **Runtimes flexíveis** | Suporta OpenClaw, Claude Code, Codex, HTTP endpoints, Bash — "se recebe heartbeat, está contratado" |

**Arquitectura proposta:**
```
Paperclip (self-hosted, PostgreSQL/Supabase)
│
├── Empresa: NoticIA PT
│   ├── Departamento: Colecta
│   │   ├── Agente Coletor RSS (heartbeat: 15min, runtime: Edge Function via HTTP)
│   │   ├── Agente Coletor GDELT (heartbeat: 15min, runtime: Edge Function via HTTP)
│   │   └── Agente Coletor Telegram (heartbeat: 5min, runtime: Fly.io HTTP)
│   │
│   ├── Departamento: Pipeline Editorial
│   │   ├── Agente Bridge (heartbeat: 20min, runtime: Edge Function via HTTP)
│   │   ├── Agente Triagem (heartbeat: 20min, runtime: Ollama DeepSeek V3.2)
│   │   ├── Agente Fact-Checker (heartbeat: 25min, runtime: Ollama Nemotron 3 Super)
│   │   └── Agente Escritor (heartbeat: 30min, runtime: Ollama Nemotron 3 Super)
│   │
│   ├── Departamento: Publicação
│   │   ├── Agente Publisher P1/P2/P3 (heartbeat: 3h/8h)
│   │   └── 10 Cronistas (heartbeat: semanal)
│   │
│   └── Departamento: Engenharia
│       └── Agente Engenheiro-Chefe v2 (heartbeat: 4h, runtime: Claude + Supabase MCP)
│
└── Empresa: NoticIA EN (futuro — P3.3 multi-idioma)
```

**Implementação:**
1. Instalar localmente: `npx paperclipai onboard --yes`
2. Criar "empresa" NoticIA PT com missão editorial
3. Migrar agentes um a um (começar pelo Engenheiro-Chefe como teste)
4. Manter pg_cron para coletores (HTTP endpoints são runtimes válidos)
5. Substituir Fly.io scheduler pelos heartbeats do Paperclip
6. Dashboard unificado substitui equipa-tecnica + DIARIO-DE-BORDO manual

**Pré-requisitos:**
- P1 completa (stored procedures, circuit breakers) — os agentes precisam de ser robustos antes de serem orquestrados
- P2.1 OU Paperclip heartbeats (não ambos — Paperclip substitui Procrastinate)

**Decisão:** Se P2.1 (Procrastinate) for implementado primeiro, Paperclip torna-se P3.5. Se decidirmos saltar P2.1, Paperclip pode ser promovido a P2.1 directamente.

**Custo:** Grátis (MIT, self-hosted). PostgreSQL existente (Supabase).

**Marketplace futuro:** Paperclip está a construir o Clipmart — marketplace de templates de empresas. O NoticIA poderia ser publicado como template "AI Newsroom" para outros projectos usarem.

---

## Cronograma Visual

```
Semana 1 (18-24 Mar):
├── P1.1 Stored Procedure atómica ✅ FEITO (commit fe12732)
├── P1.2 SALTADO — Paperclip tem heartbeats nativos
├── P1.3 Circuit breaker Tenacity+PyBreaker
├── P1.4 Alertas pg_cron → Telegram (manter como backup independente do Python)
├── P1.5 Gitleaks pre-commit
├── P1.6 Idempotência ON CONFLICT
└── 🆕 PAPERCLIP — Instalar, criar empresa NoticIA, migrar agentes

Semana 2-3 (25 Mar - 7 Abr):
├── P2.1 SALTADO — Paperclip substitui Procrastinate
├── P2.2 CI/CD completo + rollback
└── P2.3 Testes com mock LLM

Semana 4-5 (8-15 Abr):
├── P2.4 Trace IDs end-to-end
├── P2.5 Infisical secrets
└── P2.6 Supabase Sentinel RLS

Abril-Junho:
├── P3.1 Separar containers
├── P3.2 RunPod (se custos justificarem)
├── P3.3 Multi-idioma JSONB
└── P3.4 Promptfoo evals
```

---

## Métricas de Sucesso

| Métrica | Antes | Objectivo P1 | Objectivo P2 |
|---------|-------|-------------|-------------|
| Tempo até detectar falha | Horas/dias | <5 min | <1 min |
| Artigos sem fontes | ~6% (4/64) | 0% | 0% |
| Falhas silenciosas/semana | ~5 | 0 | 0 |
| Testes automatizados | 0 | 0 (P1 foca infra) | >20 |
| Tempo de recovery | Manual (horas) | <15 min | Automático |
| Secrets no git | Sim (CRIT-001) | Impossível (hook) | Centralizado |

---

*Plano criado: 2026-03-18 | Baseado em: Pesquisa LMNotebook + Auditoria Cowork*
*Próxima revisão: Após conclusão da Fase P1 (24 Mar)*
