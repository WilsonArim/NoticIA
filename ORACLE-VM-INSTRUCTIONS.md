# INSTRUÇÕES URGENTES PARA ORACLE VM
## Operação Ressuscitar Pipeline — 2026-03-20

**CONTEXTO:** A auditoria forense ao sistema revelou que os colectores pararam a 19/Mar ~16:00 UTC. O site continua a publicar artigos do backlog da intake_queue, mas sem novos raw_events o sistema vai secar em breve. Além disso, artigos de desporto continuam a ser publicados apesar da área estar desactivada.

---

## DIAGNÓSTICO ACTUAL (dados Supabase, 20/Mar 15:00 UTC)

### Raw Events — Última Recolha por Colector
| Colector | Última Recolha | Total Histórico |
|----------|---------------|-----------------|
| RSS | 2026-03-19 16:00 | 13,500 |
| GDELT | 2026-03-19 15:45 | 1,569 |
| X-Cowork | 2026-03-17 09:26 | 386 |
| X | 2026-03-14 23:32 | 110 |

### Pipeline Runs (últimos 3 dias)
| Stage | Último Run | Total Runs | Status |
|-------|-----------|------------|--------|
| filter | 19/Mar 16:00 | 84 | ✅ Foi activo |
| equipa_tecnica | 19/Mar 09:15 | 8 | ✅ Foi activo |
| collect | 18/Mar 10:49 | 54 | ✅ Foi activo |
| triagem | 17/Mar 16:20 | 1 | ⚠️ Legacy |
| dispatcher | — | 0 | ❌ NUNCA LOGOU |
| fact_checker | — | 0 | ❌ NUNCA LOGOU |
| escritor | — | 0 | ❌ NUNCA LOGOU |

### Intake Queue (após limpeza)
| Status | Total |
|--------|-------|
| pending | 1,930 |
| auditor_approved | 1,774 |
| fact_check | 870 |

### Artigos Publicados Hoje (20/Mar)
13 artigos publicados — TODOS do backlog, incluindo 2 de desporto (área desactivada).

---

## ACÇÕES A EXECUTAR NA ORACLE VM

### PASSO 1: Verificar se o scheduler está a correr

```bash
# Verificar systemd service
sudo systemctl status openclaw

# Se não for systemd, verificar processos
ps aux | grep scheduler_ollama
ps aux | grep python | grep openclaw

# Ver logs recentes
sudo journalctl -u openclaw --since "2026-03-19" --no-pager | tail -100

# Se não for systemd, verificar logs do screen/tmux/nohup
ls -la /home/opc/openclaw/logs/
cat /home/opc/openclaw/logs/scheduler.log | tail -100
```

**Se o scheduler NÃO está a correr:** Reiniciar com:
```bash
cd /home/opc/openclaw/pipeline  # ou o path correcto
nohup python -m openclaw.scheduler_ollama > /home/opc/openclaw/logs/scheduler.log 2>&1 &
```

**Se o scheduler ESTÁ a correr mas os colectores pararam:** Verificar erros:
```bash
# Procurar erros de API/timeout
grep -i "error\|exception\|traceback\|timeout\|429\|403" /home/opc/openclaw/logs/scheduler.log | tail -50
```

---

### PASSO 2: Verificar variáveis de ambiente

```bash
# Verificar se as env vars existem
echo "SUPABASE_URL=$SUPABASE_URL"
echo "SUPABASE_SERVICE_KEY existe: $([ -n "$SUPABASE_SERVICE_KEY" ] && echo SIM || echo NAO)"
echo "OLLAMA_BASE_URL=$OLLAMA_BASE_URL"
echo "OLLAMA_API_KEY existe: $([ -n "$OLLAMA_API_KEY" ] && echo SIM || echo NAO)"
echo "EVENT_REGISTRY_API_KEY existe: $([ -n "$EVENT_REGISTRY_API_KEY" ] && echo SIM || echo NAO)"
echo "TAVILY_API_KEY existe: $([ -n "$TAVILY_API_KEY" ] && echo SIM || echo NAO)"
echo "EXA_API_KEY existe: $([ -n "$EXA_API_KEY" ] && echo SIM || echo NAO)"

# CRÍTICO: Verificar se OLLAMA_BASE_URL aponta para OpenRouter (não localhost)
# Deve ser algo como: https://openrouter.ai/api/v1
echo "OLLAMA_BASE_URL=$OLLAMA_BASE_URL"
```

---

### PASSO 3: Desactivar desporto no pipeline

O ficheiro `config.py` tem as áreas GDELT. Desporto precisa de ser removido:

```bash
# Localizar o config
find /home/opc -name "config.py" -path "*/openclaw/*" 2>/dev/null

# Editar config.py — REMOVER "sports" das GDELT_AREAS
# A linha será algo como:
# GDELT_AREAS = { "geopolitics": "...", ..., "sports": "...", ... }
# REMOVER a entrada "sports" completamente
```

**Alternativamente**, adicionar filtro no dispatcher.py para rejeitar área "desporto":

```python
# No dispatcher.py, na função _classify_event, após parse do JSON:
DISABLED_AREAS = {"desporto", "sports"}
if area.lower() in DISABLED_AREAS:
    continue  # Saltar esta área
```

---

### PASSO 4: Verificar por que o dispatcher/fact_checker/escritor não logam a pipeline_runs

Os 3 agentes principais (dispatcher, fact_checker, escritor) estão a funcionar (há artigos publicados hoje), mas **NUNCA registaram** em pipeline_runs. Isto significa que o código deles não usa a função de logging.

**Verificar se existe logging no código:**
```bash
grep -r "pipeline_runs" /home/opc/openclaw/pipeline/src/openclaw/agents/
grep -r "pipeline_runs" /home/opc/openclaw/pipeline/src/openclaw/
```

Se NÃO existe, adicionar logging ao início e fim de cada run. Exemplo para dispatcher.py:

```python
# No início de run_dispatcher():
import datetime
run_id = supabase.table("pipeline_runs").insert({
    "stage": "dispatcher",
    "status": "running",
    "started_at": datetime.datetime.utcnow().isoformat(),
    "events_in": 0,
    "events_out": 0
}).execute().data[0]["id"]

# No fim (sucesso):
supabase.table("pipeline_runs").update({
    "status": "completed",
    "completed_at": datetime.datetime.utcnow().isoformat(),
    "events_in": total_processed,
    "events_out": total_classified
}).eq("id", run_id).execute()
```

Fazer o mesmo para `fact_checker.py` e `escritor.py`.

---

### PASSO 5: Verificar Paperclip (se ainda corre)

```bash
# Paperclip corre na porta 3100
curl -s http://localhost:3100/health || echo "Paperclip NÃO está a correr"

# Se estiver a correr, verificar o adapter
curl -s http://localhost:3100/api/agents | python3 -m json.tool | head -50
```

**DECISÃO ARQUITECTURAL:** O Paperclip tem o adapter_type 'claude_local' que é agora dummy (após remoção do Claude CLI). Opções:

**Opção A (RECOMENDADA):** Manter Paperclip apenas como UI de monitorização. Todo o trabalho real é feito pelo Python scheduler. Paperclip NÃO executa agentes — apenas mostra o estado.

**Opção B:** Alterar o adapter para chamar Edge Functions ou o Python directamente. Mais complexo, não prioritário.

---

### PASSO 6: Corrigir triagem legacy

A `run_triagem()` no scheduler processa items com status='pending'. Isto é legacy — o dispatcher agora insere directamente com status='auditor_approved'.

**Há 1930 items pending na queue** que foram inseridos antes do dispatcher estar activo. A triagem pode processá-los, mas depois deve ser desactivada:

```bash
# APÓS processar os pending existentes, comentar a triagem no scheduler:
# No scheduler_ollama.py, comentar:
# scheduler.add_job(run_triagem, 'interval', minutes=20, ...)
```

---

### PASSO 7: Reiniciar colectores e verificar

Após os passos anteriores:

```bash
# Reiniciar o scheduler
sudo systemctl restart openclaw
# OU
kill $(pgrep -f scheduler_ollama) && sleep 2
cd /home/opc/openclaw/pipeline
nohup python -m openclaw.scheduler_ollama > logs/scheduler.log 2>&1 &

# Verificar se os colectores estão a funcionar (esperar 15 min)
# Depois verificar no Supabase:
# SELECT source_collector, MAX(fetched_at), COUNT(*) FROM raw_events WHERE fetched_at > NOW() - INTERVAL '1 hour' GROUP BY source_collector;
```

---

## RESUMO DO QUE FOI FEITO HOJE (Cowork Session)

### Edge Functions Neutralizadas (9 fantasmas → no-op)
1. ✅ `bridge-events` — substituído por dispatcher.py
2. ✅ `grok-reporter` — Grok API eliminada
3. ✅ `grok-fact-check` — Grok API eliminada
4. ✅ `grok-bias-check` — Grok API eliminada
5. ✅ `source-finder` — substituído por reporters Python
6. ✅ `reporter-filter` — substituído por dispatcher.py
7. ✅ `curator-central` — substituído por curador.py
8. ✅ `collect-x-grok` — Grok API eliminada
9. ✅ `collect-x` — substituído por coletor-x.py

### Intake Queue Limpa
- **Antes:** 5,937 items (desporto spam, duplicados, rejeitados, processados)
- **Depois:** 4,574 items limpos (1,930 pending + 1,774 auditor_approved + 870 fact_check)
- Removidos: toda a área desporto, todos auditor_failed, editor_rejected, failed, processed
- Normalizados: "Defesa"→"defesa", "Geopolitica"/"geopolítica"→"geopolitica"

### Agentes Supabase (53 total)
- Todos os 53 agentes têm `system_prompt` + `promptTemplate` + `capabilities` configurados
- Organização hierárquica: 7 colectores, 1 dispatcher, 14 reporters, 6 FC sectoriais, 3 editorial, 3 publishers, 10 cronistas, 4 engenheiros, 5 elite

### Arquitectura Limpa
- **Motor Python** (scheduler_ollama.py): É o motor real — colectores, dispatcher, fact-check, escritor
- **Paperclip**: UI de monitorização apenas — adapter dummy desde remoção do Claude CLI
- **Edge Functions activas (legítimas)**: receive-article, receive-claims, receive-rationale, agent-log, publish-article, e outras de suporte ao frontend

---

## PRIORIDADE MÁXIMA

1. **REINICIAR COLECTORES** — O site vai secar sem novos raw_events
2. **DESACTIVAR DESPORTO** — Artigos de desporto estão a ser publicados sem verificação
3. **ADICIONAR LOGGING** — Dispatcher/FC/Escritor não logam a pipeline_runs, impossível monitorizar
4. **PROCESSAR PENDING** — 1,930 items pending podem ser processados pela triagem antes de a desactivar

---

*Documento gerado automaticamente pela sessão Cowork de 2026-03-20.*
*Para dúvidas: consultar ARCHITECTURE-MASTER.md e DIARIO-DE-BORDO.md*
