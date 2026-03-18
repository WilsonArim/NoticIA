# Prompt para Claude Code — Fix Fly.io Scheduler (noticia-scheduler)

Lê primeiro: `CLAUDE.md`, `docs/PIPELINE-MAP.md`, `docs/DIARIO-DE-BORDO.md`

---

## CONTEXTO

O Fly.io app `noticia-scheduler` corre o pipeline LLM: triagem → fact-checker → escritor → dossiê.
Após deploy, as máquinas ficam com leases órfãs e não arrancam correctamente.
O scheduler precisa de ser reiniciado limpo.

**Ficheiros relevantes:**
- `pipeline/fly.toml` — config Fly.io
- `pipeline/Dockerfile` — Python 3.11-slim
- `pipeline/src/openclaw/scheduler_ollama.py` — scheduler APScheduler

**Último commit:** `1c301d1` — fix misfire_grace_time + offset fact_checker

---

## TAREFA 1 — Limpar máquinas e redeploy limpo

```bash
cd pipeline

# 1. Ver estado actual
fly status --app noticia-scheduler

# 2. Listar máquinas
fly machines list --app noticia-scheduler

# 3. Destruir TODAS as máquinas (leases órfãs impedem update)
# Substituir IDs pelos que aparecerem no passo 2
fly machines destroy <ID1> --force --app noticia-scheduler
fly machines destroy <ID2> --force --app noticia-scheduler

# 4. Deploy limpo (cria máquinas novas)
fly deploy --app noticia-scheduler

# 5. Verificar que arrancou
fly status --app noticia-scheduler
# STATE deve ser "started"
```

---

## TAREFA 2 — Verificar scheduler arrancou correctamente

```bash
# Esperar 30 segundos após deploy, depois:
fly logs --app noticia-scheduler --no-tail | tail -30
```

**Deve mostrar (por esta ordem):**
1. `Iniciando scheduler Ollama — DeepSeek V3.2 + Nemotron 3 Super`
2. `Dossiê: iniciando ciclo para N temas` (startup — corre dossiê primeiro)
3. `Triagem: processando N items` ou `Triagem: sem items pendentes` (startup — corre triagem depois)
4. `Added job "run_triagem"` / `"run_fact_checker"` / `"run_escritor"` / `"run_dossie"`
5. `Scheduler started`
6. `Scheduler activo.`

**Se faltar alguma destas linhas:** o scheduler crashou no arranque. Ver erros com:
```bash
fly logs --app noticia-scheduler --no-tail | grep -i "error\|ERROR\|traceback\|exception"
```

---

## TAREFA 3 — Esperar e verificar que TODOS os jobs disparam

Os intervalos são:
- `run_triagem`: cada **20 min** (primeiro disparo ~20min após start)
- `run_fact_checker`: cada **25 min** (primeiro disparo ~25min após start)
- `run_escritor`: cada **30 min** (primeiro disparo ~30min após start)
- `run_dossie`: cada **6h**

**Esperar 35 minutos após "Scheduler activo."** e depois verificar:

```bash
# TODOS os três devem aparecer:
fly logs --app noticia-scheduler --no-tail | grep -i "Running job"
```

**Output esperado (3 linhas mínimas):**
```
Running job "run_triagem (trigger: interval[0:20:00], next run at: ...)"
Running job "run_fact_checker (trigger: interval[0:25:00], next run at: ...)"
Running job "run_escritor (trigger: interval[0:30:00], next run at: ...)"
```

**Se `run_escritor` NÃO aparecer:**
O APScheduler está a saltar o job. Verificar com:
```bash
fly logs --app noticia-scheduler --no-tail | grep -i "escritor"
```

Se zero resultados, o problema é misfire_grace_time. O ficheiro `scheduler_ollama.py` já tem `misfire_grace_time=120` e os intervalos estão desfasados (20/25/30 min). Se mesmo assim não dispara, aumentar o desfasamento:
```python
# Em scheduler_ollama.py:
scheduler.add_job(run_fact_checker, IntervalTrigger(minutes=23), ...)  # 23 min
scheduler.add_job(run_escritor, IntervalTrigger(minutes=31), ...)      # 31 min
```

---

## TAREFA 4 — Verificar artigos publicados

Após o escritor correr (ver "Running job run_escritor" nos logs), verificar:

```bash
fly logs --app noticia-scheduler --no-tail | grep -i "artigo publicado\|Escritor erro"
```

**Sucesso:** `Escritor: artigo publicado 'Título do Artigo'`
**Erro:** `Escritor erro item UUID: mensagem de erro`

Verificar também no Supabase:
```sql
SELECT count(*) as novos, max(created_at) as ultimo
FROM articles WHERE created_at > now() - interval '1 hour';
```

Se `novos > 0`: pipeline completa a funcionar.

---

## TAREFA 5 — Validação final end-to-end

Correr esta query para confirmar que TODA a pipeline flui:

```sql
SELECT
  (SELECT count(*) FROM raw_events WHERE created_at > now() - interval '1 hour') as raw_1h,
  (SELECT count(*) FROM intake_queue WHERE status = 'pending') as pending,
  (SELECT count(*) FROM intake_queue WHERE status = 'auditor_approved') as triados,
  (SELECT count(*) FROM intake_queue WHERE status = 'approved') as verificados,
  (SELECT count(*) FROM articles WHERE created_at > now() - interval '2 hours') as artigos_2h;
```

**Pipeline saudável:**
- `raw_1h > 0` — coletores a alimentar
- `pending` baixo (< 10) — triagem a processar
- `triados` a diminuir entre ciclos — fact-checker a processar
- `verificados` a diminuir entre ciclos — escritor a publicar
- `artigos_2h > 0` — artigos novos no site

---

## TROUBLESHOOTING

**"Failed to clear lease":**
Máquinas com leases órfãs. Destruir todas com `--force` e redeploy.

**"Scheduler activo" mas jobs não disparam:**
Misfire_grace_time demasiado baixo. Já corrigido para 120s no commit `1c301d1`.

**Escritor erro "SyncQueryRequestBuilder has no attribute select":**
Já corrigido no commit `25593a5`. Se reaparecer, verificar que o deploy usou o código mais recente (step [6/8] COPY src/ NÃO deve ser CACHED).

**Fact-checker rejeita tudo (certainty=0.00):**
O modelo Nemotron retorna 0.00 quando não encontra fontes. Normal para artigos em línguas não-inglesas ou temas obscuros. Não é bug.

**Zero raw_events:**
Verificar pg_cron jobs: `SELECT jobname, schedule, active FROM cron.job;`
Devem existir: collect-rss (*/15), collect-gdelt (*/15), bridge-events (*/20).
