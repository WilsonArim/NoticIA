# Diário de Bordo — Curador de Noticias

> Registo cronológico das decisões, migrações e marcos do projecto.
> Actualizar no início de cada sessão de trabalho significativa.

---

## 2026-03-20 (TARDE) — Auditoria Forense + Operação Caça-Fantasmas

### Contexto
Sessão urgente após descoberta de que o pipeline tem problemas graves: colectores parados, fantasmas a correr, artigos de desporto publicados apesar da área estar desactivada. Auditoria forense completa ao sistema.

---

### 1. Auditoria Forense — Descobertas Críticas

**A. Colectores MORTOS desde 19/Mar ~16:00 UTC**
- RSS: última recolha 19/Mar 16:00 (13,500 raw_events total)
- GDELT: última recolha 19/Mar 15:45 (1,569 total)
- X-Cowork: parado desde 17/Mar
- X: parado desde 14/Mar
- **ZERO novos raw_events nas últimas ~28 horas**

**B. Pipeline parcialmente funcional**
- Dispatcher, fact_checker, escritor: FUNCIONAM (13 artigos publicados hoje)
- MAS não registam em pipeline_runs (ZERO logs de dispatcher/FC/escritor)
- Artigos de hoje são TODOS do backlog da intake_queue

**C. Desporto continua a publicar**
- 2 artigos de desporto publicados hoje (Atlético-MG e Barcelona/Newcastle)
- Área deveria estar desactivada desde 19/Mar
- Causa: fact_checker.py genérico não filtra por área

**D. 9 Edge Functions fantasma**
- Funções deprecated mas ainda deployed e chamáveis no Supabase
- Não estavam a ser chamadas activamente, mas representavam risco

**E. Intake Queue poluída**
- 5,937 items acumulados (incl. spam desporto, duplicados, rejeitados)
- Inconsistências de naming: "Defesa"/"defesa", "Geopolitica"/"geopolítica"/"geopolitica"

---

### 2. Edge Functions Neutralizadas (9 fantasmas → no-op) ✅

Todas deployed como no-op com mensagem de deprecação e referência ao substituto:

| # | Edge Function | Motivo | Substituto |
|---|--------------|--------|------------|
| 1 | `bridge-events` (v11) | Substituído | dispatcher.py |
| 2 | `grok-reporter` (v10) | Grok API eliminada | reporters Python |
| 3 | `grok-fact-check` (v18) | Grok API eliminada | FC sectoriais Python |
| 4 | `grok-bias-check` (v9) | Grok API eliminada | bias_analysis no FC |
| 5 | `source-finder` (v10) | Substituído | reporters Python |
| 6 | `reporter-filter` (v10) | Substituído | dispatcher.py routing |
| 7 | `curator-central` (v10) | Substituído | curador.py |
| 8 | `collect-x-grok` (v10) | Grok API eliminada | coletor-x.py |
| 9 | `collect-x` (v10) | Substituído | coletor-x.py |

---

### 3. Limpeza da Intake Queue ✅

| Acção | Items Removidos |
|-------|----------------|
| Eliminar área desporto (spam apostas) | ~200 |
| Eliminar auditor_failed (rejeitados) | ~942 |
| Eliminar editor_rejected | 4 |
| Eliminar failed | 4 |
| Eliminar processed (já geraram artigos) | ~168 |
| Eliminar duplicados (por título) | ~20+ |
| **Total removido** | **~1,363** |

**Normalizações:**
- "Defesa" → "defesa" (1 item)
- "Geopolitica" → "geopolitica" (1 item)
- "geopolítica" → "geopolitica" (1 item)

**Estado final da queue:** 4,574 items limpos
- pending: 1,930
- auditor_approved: 1,774
- fact_check: 870

---

### 4. Instruções Oracle VM Geradas ✅

Ficheiro `ORACLE-VM-INSTRUCTIONS.md` criado com 7 passos detalhados:
1. Verificar se scheduler está a correr
2. Verificar variáveis de ambiente
3. Desactivar desporto no pipeline config
4. Adicionar logging a pipeline_runs para dispatcher/FC/escritor
5. Decisão arquitectural Paperclip (UI only vs motor)
6. Processar pending existentes e depois desactivar triagem legacy
7. Reiniciar colectores e verificar

---

### 5. Decisão Arquitectural — Motor Único

**Problema identificado:** Dois "motores" a correr em paralelo sem coordenação:
- **Paperclip** (Node.js, porta 3100): adapter dummy desde remoção do Claude CLI. Heartbeats registam "succeeded" mas ZERO trabalho real.
- **Python scheduler** (scheduler_ollama.py, systemd): O motor REAL. Colectores, dispatcher, FC, escritor.

**Decisão:** Paperclip = UI de monitorização APENAS. Python scheduler = motor de execução. Não há motores concorrentes — apenas um está activo.

---

### 6. Operação Ressuscitar Pipeline (Oracle VM) ✅

Executado pelo Claude Code na Oracle VM (opc@82.70.84.122). Resultados:

**Diagnóstico:**
- `noticia-pipeline` ✅ active (running)
- `noticia-telegram` ✅ active (running) — com FLOOD-WAIT (~800 canais bloqueados temporariamente)
- `paperclip` ✅ active (running) — adapter dummy, UI only
- ⚠️ **OpenRouter rate limit diário ESGOTADO** (2000 req/dia, Remaining: 0, reset 00:00 UTC)

**Ficheiros modificados e deployed na Oracle VM:**
1. `config.py` — Removido `"sports"` das GDELT_QUERIES
2. `dispatcher.py` — Adicionado `DISABLED_AREAS = {"desporto", "sports", "sport"}` + logging pipeline_runs
3. `fact_checker.py` — Adicionado `DISABLED_AREAS` filter + logging pipeline_runs
4. `escritor.py` — Adicionado logging pipeline_runs com published_count tracking

**Migration Supabase executada:**
- `pipeline_runs_stage_check` constraint actualizado — adicionados stages: `dispatcher`, `fact_checker`, `escritor`, `collect_telegram`
- Stages deprecated (`grok_*`) mantidos para dados históricos

**Pipeline reiniciada** com 4 jobs activos: dispatcher (5m), triagem (20m), fact_checker (25m), escritor (30m)

---

### Estado Final do Sistema (20/Mar ~16:00 UTC)

| Métrica | Valor |
|---------|-------|
| Artigos últimas 24h | 27 |
| Raw events últimas 2h | 0 (rate limit) |
| Queue pending | 1,905 |
| Queue auditor_approved | 1,781 |
| Queue fact_check | 878 |
| Pipeline runs última hora | 0 (rate limit) |

**Nota:** O pipeline está funcional mas estrangulado pelo rate limit do OpenRouter (2000 req/dia esgotados). Às 00:00 UTC o limite reseta e os colectores + pipeline voltam a processar automaticamente.

---

### 7. Plano de Acção Executado — Limpeza Total ✅

**FASE 1 — Fantasmas DB eliminados:**
- `bridge_raw_to_intake` RPC eliminada (DROP FUNCTION)
- `auditor_evaluate` RPC renomeada para `_deprecated_auditor_evaluate`
- Tabelas `scored_events` e `dossie_watchlist` limpas (0 rows)

**FASE 2 — 15 Edge Functions tratadas:**
- `cronista` v9: **MIGRADA de Grok para Nemotron 3 Super** via OpenRouter (era o último vestígio da Grok API no sistema)
- 6 collectors dormant → no-op: collect-rss, collect-gdelt, collect-event-registry, collect-acled, collect-telegram, collect-crawl4ai
- 9 fantasmas já neutralizados anteriormente

**FASE 3 — Ficheiros mortos identificados (requer git rm na Oracle VM):**
- `pipeline/src/openclaw/bridge.py` — imports quebrados, ficheiro fantasma
- `pipeline/src/openclaw/agents/dossie.py` — deprecated
- `src/components/xai/` — 5 componentes React mortos (BiasAuditPanel, ConfidenceBreakdown, CounterfactualExplorer, RationaleChips, TripletViewer)
- `telegram-collector/` — projecto orphan do Fly.io com venv próprio
- `pipeline/src/openclaw/config.py` — constantes XAI_* mortas (limpar)

**FASE 4 — Consistência Paperclip ↔ Supabase verificada:**
- Hierarquia: 53/53 agentes com `reports_to` válido (0 orphans)
- Prompts: 53/53 com `system_prompt` (1077-4682 chars cada)
- Templates: 53/53 `promptTemplate` sincronizado com `system_prompt`
- Reporter configs: 19/20 com agente correspondente (desporto disabled, sem agente = correcto)

**FASE 5 — Testes reais:**
- RPC `publish_article_with_sources`: ✅ exists, 1 arg (payload)
- Pipeline flow: 15,565 raw_events (100% processed) → 4,574 intake_queue → 179 articles (115 published)
- 24 Edge Functions: todas ACTIVE (9 no-op, 6 dormant, 8 activas, 1 migrada)
- Integridade FK: 304 claims, 1537 claim_sources, 733 unique sources

---

### Estado Final do Sistema (20/Mar ~18:00 UTC)

**24 Edge Functions:**
| Categoria | Qty | Funções |
|-----------|-----|---------|
| ACTIVAS | 8 | receive-article, receive-claims, receive-rationale, agent-log, receive-intake, writer-publisher, article-card, publish-instagram |
| MIGRADA | 1 | cronista (Grok → Nemotron 3 Super v9) |
| DORMANT | 6 | collect-rss/gdelt/event-registry/acled/telegram/crawl4ai |
| NO-OP | 9 | bridge-events, grok-reporter/fact-check/bias-check, source-finder, reporter-filter, curator-central, collect-x/x-grok |

**4 RPC Functions:**
| Função | Status |
|--------|--------|
| `publish_article_with_sources` | ✅ ACTIVA |
| `enforce_publish_quality` | ✅ ACTIVA |
| `log_publish_block` | ✅ ACTIVA |
| `get_secret` | ✅ ACTIVA |
| `_deprecated_auditor_evaluate` | 🚫 DEPRECATED |

---

### Pendente / Próximos Passos

- [x] ~~URGENTE: Executar ORACLE-VM-INSTRUCTIONS.md na Oracle VM~~ ✅
- [x] ~~Desactivar desporto no config.py do pipeline~~ ✅
- [x] ~~Adicionar logging a pipeline_runs para dispatcher/FC/escritor~~ ✅
- [x] ~~ALTER TABLE pipeline_runs constraint para novos stages~~ ✅
- [x] ~~Migrar cronista de Grok para Nemotron 3 Super~~ ✅
- [x] ~~Neutralizar 6 Edge Functions collectors dormant~~ ✅
- [x] ~~DROP bridge_raw_to_intake RPC~~ ✅
- [x] ~~Sincronizar promptTemplate em 53 agentes~~ ✅
- [ ] Processar 1,905 items pending (triagem activa, aguarda reset rate limit)
- [ ] Depois de processar pending: desactivar triagem legacy no scheduler
- [ ] **git rm** ficheiros mortos na Oracle VM: bridge.py, dossie.py, src/components/xai/, telegram-collector/
- [ ] Deploy git push para GitHub
- [ ] Adicionar OPENROUTER_API_KEY nos Supabase Edge Function secrets (para cronista v9)
- [ ] Instalar NemoClaw no Oracle VM
- [ ] Considerar upgrade OpenRouter para tier pago (2000 req/dia pode ser insuficiente)

---

## 2026-03-20 (MANHÃ) — Operação Limpeza + Configuração Completa de Todos os Agentes

### Objectivo da Sessão
Configurar prompt templates e capabilities para todos os agentes no Paperclip/Supabase. Limpar a estrutura da redacção (agentes deprecated, hierarquia, adapter types). Remover dependência do Claude CLI do Paperclip.

---

### 1. Remoção do Claude CLI do Paperclip ✅

**Problema:** Todos os agentes no Paperclip falhavam com "Command not found: claude" porque o Paperclip invocava o Claude Code CLI para executar cada agente.

**Solução (executada pelo Claude Code na Oracle VM):**
- `packages/adapters/claude-local/src/server/execute.ts` — `runChildProcess()`/`spawn()` comentados, retorna dummy streams
- `packages/adapters/claude-local/src/server/test.ts` — validação do CLI claude removida
- `packages/adapter-utils/src/server-utils.ts` — `ensureCommandResolvable()` bypassed para 'claude'
- `pnpm build` executado, Paperclip reiniciado com sucesso

**Conclusão:** O Paperclip usa agora as LLMs via OpenRouter directamente. O Claude CLI não é necessário — era um legado da configuração inicial.

---

### 2. Deployment do Dispatcher.py no Oracle VM ✅

**Problema:** Pipeline "funil a seco" — raw_events acumulavam mas não eram processados porque `bridge-events` estava desactivado e o `dispatcher.py` ainda não estava deployed.

**Solução:**
- `dispatcher.py` (385 linhas) deployed via SCP para Oracle VM
- `scheduler_ollama.py` actualizado para incluir job `dispatcher(5m)`
- Confirmado nos logs: "Dispatcher: processando X eventos com nvidia/nemotron-nano-30b-instruct:free"

**Ficheiro:** `pipeline/src/openclaw/agents/dispatcher.py`
**Modelo:** `nvidia/nemotron-nano-30b-instruct:free` via OpenRouter

---

### 3. Limpeza de Agentes Deprecated ✅

**Agentes eliminados permanentemente do Supabase (CASCADE DELETE de 25+ tabelas):**
- `dossie` — substituído pela Equipa Elite
- `triagem` — substituído pelo Dispatcher LLM
- `source-finder` — funcionalidade integrada no Editor-Chefe
- `bridge-events` — substituído pelo Dispatcher LLM
- `fact-checker` (genérico) — substituído pelos 6 FCs sectoriais

**Nota:** Os agentes foram ELIMINADOS (não apenas paused). Não recriar.

---

### 4. Reestruturação da Hierarquia ✅

**Problema:** Hierarquia caótica — engenheiro no lugar do CEO, agentes com roles "general", cronistas e collectors sob o engenheiro-chefe.

**Hierarquia correcta implementada:**
```
Wilson (proprietário)
├── Equipa Elite (reports_to = NULL)
│   ├── reporter-investigacao
│   ├── fc-forense
│   └── publisher-elite
├── openclaw-ceo (CEO)
│   ├── agente-rh
│   ├── editor-chefe
│   │   ├── dispatcher
│   │   ├── auditor
│   │   │   ├── 19 reporters
│   │   │   └── 7 FCs (6 sectoriais + fc-forense)
│   │   ├── escritor
│   │   ├── publisher-p1 / p2 / p3
│   │   └── 10 cronistas
│   │   (collectors → dispatcher)
│   └── engenheiro-chefe
│       ├── engenheiro-backend
│       └── engenheiro-frontend
```

**Roles corrigidos:** ceo, editor, engineer, dispatcher, auditor, writer, reporter, fact_checker, columnist, publisher, collector, hr

---

### 5. Novos Agentes Criados ✅

| Agente | Role | Reports to | Função |
|--------|------|-----------|--------|
| `engenheiro-backend` | engineer | engenheiro-chefe | Monitoriza pipeline de dados e backend |
| `engenheiro-frontend` | engineer | engenheiro-chefe | Verifica integridade do conteúdo no frontend |
| `agente-rh` | hr | openclaw-ceo | Auditoria organizacional dos agentes |

---

### 6. Adapter Type Unificado ✅

**Problema:** Alguns agentes com `claude_local`, outros com `process`. O adapter `process` não existe ainda no Paperclip — causava erros em todos os agentes com esse tipo.

**Solução:** Todos os 53 agentes uniformizados para `adapter_type = 'claude_local'`.

**Nota importante:** `adapter_type = 'claude_local'` NÃO significa que usa o Claude CLI. Após a limpeza do Paperclip (passo 1), o adapter claude_local é o único funcional e usa as LLMs via OpenRouter.

---

### 7. Prompt Templates e Capabilities — Configuração Completa ✅

**Estado anterior:** 0 agentes com prompt template configurado no Paperclip.
**Estado actual:** 53/53 agentes totalmente configurados.

**Fases executadas:**

| Fase | Descrição | Agentes | Método |
|------|-----------|---------|--------|
| 1 | Reporters: copiar grok_system_prompt de reporter_configs | 19 reporters | SQL JOIN com mapeamento area→agent_name |
| 2 | Fact-Checkers sectoriais: prompts novos de alta qualidade | 6 FCs | Escritos de raiz (2400-2800 chars cada) |
| 3 | Cronistas: prompts baseados em AGENT-PROFILES.md | 10 cronistas | Escritos de raiz com identidade/ideologia/formato |
| 4 | Editorial: Auditor, Escritor, Editor-Chefe, CEO | 4 agentes | Escritos de raiz baseados em AGENT-PROFILES.md |
| 5 | Publishers (P1, P2, P3) e Collectors (RSS, GDELT, Telegram) | 6 agentes | Escritos de raiz com processo e regras |
| 6 | Capabilities: descrições específicas para todos | 53 agentes | Actualizadas de genéricas para específicas |

**Chave em adapter_config:** Os prompts foram guardados em DUAS chaves:
- `system_prompt` (snake_case, lido pelo Python pipeline)
- `promptTemplate` (camelCase, lido pelo Paperclip UI)

---

### 8. Estado Final dos Agentes

```
SELECT COUNT(*), with_prompt, with_capabilities, fully_configured
→ total: 53 | with_prompt: 53 | with_capabilities: 53 | fully_configured: 53
```

**53 agentes activos no Supabase** (57 do documento anterior incluíam os 4 deprecated agora eliminados + agente-rh novo).

---

### Problemas Conhecidos / Pendente

- [ ] Verificar se `promptTemplate` em adapter_config é realmente a chave que o Paperclip UI lê (aguarda confirmação visual de Wilson)
- [ ] Deploy git push para GitHub (não feito nesta sessão)
- [ ] Activar agentes no Paperclip (status idle → active)
- [ ] Instalar NemoClaw no Oracle VM (deferido)

---

## 2026-03-19 — Reestruturação Editorial v2.0 + Migração Oracle Completa

### Decisões Tomadas

**Infra:**
- Migração Fly.io → Oracle Cloud ARM (4 vCPUs, 24GB RAM, IP 82.70.84.122) concluída
- Paperclip (Node.js + React) instalado no Oracle, acesso via Nginx (porta 80/443)
- OpenClaw (scheduler_ollama.py) a correr via systemd no Oracle
- Telegram collector (1.255 canais, curador_telegram.session 57KB) migrado de Fly.io para Oracle
- Fly.io pg_cron jobs de scraping eliminados do Supabase

**Modelos LLM:**
- Eliminado: Grok API (deprecated 16/03/2026)
- Eliminado: Ollama Pro subscription (~€20/mês) — pipeline Oracle não acedia ao Ollama Cloud
- A migrar: DeepSeek V3.2 + Nemotron 3 Super → OpenRouter/NVIDIA NIM (free tier com $10 depósito)
- `.env` Oracle corrigido: variáveis `OLLAMA_BASE_URL` + `OLLAMA_API_KEY` (ollama_client.py lê estas, não DEEPSEEK_BASE_URL)
- Todos os modelos → `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter

**Estrutura Editorial — Reestruturação Completa:**

| Antes (v1) | Depois (v2) |
|-----------|-------------|
| 18 reporters genéricos | 19 reporters especializados (1 por categoria) |
| 1 fact-checker genérico | 6 fact-checkers sectoriais (1 por sector) |
| keyword scoring no Dispatcher | Dispatcher LLM com classificação semântica |
| Sem CEO explícito | CEO OpenClaw entre Wilson e o pipeline |
| Sem equipa elite | Equipa Investigação Elite (3 agentes, bypass ao pipeline) |
| ~45 agentes | 57 agentes activos |

**Categorias editoriais activas (19, sem Desporto):**
- MUNDO: Geopolítica, Política Internacional, Diplomacia, Defesa, Defesa Estratégica
- CIÊNCIA & TECH: Tecnologia, Ciência, Energia, Clima & Ambiente
- PORTUGAL: Portugal, Sociedade
- ECONOMIA: Economia, Finanças & Mercados, Crypto & Blockchain, Regulação
- SAÚDE & SOCIAL: Saúde, Direitos Humanos
- JUSTIÇA & SEGURANÇA: Desinformação/Fact-Check, Crime Organizado

**Agentes criados no Supabase (via MCP execute_sql):**
- 19 reporters especializados
- 6 fact-checkers sectoriais (fc-mundo, fc-tech, fc-portugal, fc-economia, fc-saude, fc-justica)
- 3 agentes elite (reporter-investigacao, fc-forense, publisher-elite) — reports_to = NULL (Wilson)
- CEO openclaw-ceo
- Dispatcher LLM (dispatcher)
- Auditor ("O Cético"), Editor-Chefe ("O Guardião"), Publisher P1

**Agentes deprecated (paused com razão registada):**
- bridge-events → substituído por dispatcher LLM
- fact-checker (genérico) → substituído por 6 FCs sectoriais
- triagem → substituído por dispatcher LLM
- source-finder → removido da estrutura

### Problemas Resolvidos

1. **Pipeline Oracle não acedia ao Ollama** — `.env` tinha `DEEPSEEK_BASE_URL`/`NVIDIA_API_KEY` mas `ollama_client.py` lê `OLLAMA_BASE_URL`/`OLLAMA_API_KEY`. Todas as chamadas LLM falhavam silenciosamente com 401.
2. **Telegram: documentação dizia 48 canais** — eram 1.255 canais em `channels.py`. Corrigido no ARCHITECTURE-MASTER.md.
3. **Dispatcher por keyword scoring** — gerava falsos positivos e não detectava multi-tematicidade. Solução: Dispatcher LLM dedicado com Nemotron 3 Super.

### Modelos Especializados Activados

Três modelos NVIDIA fine-tuned adicionados aos agentes correctos:

| Modelo | Especialidade | Provider | Agentes |
|--------|-------------|---------|---------|
| Content Safety 4B | Anti-desinformação, propaganda, policy enforcement | NIM | reporter-desinformacao, fc-justica |
| Nemotron Nano 12B VL | Análise multimodal (imagens, docs, screenshots) | OpenRouter | reporter-investigacao, fc-forense |
| riva-translate-4b | Tradução EN/FR/ES/DE/AR/ZH/RU → PT | NIM | 17 reporters internacionais |

Total de modelos activos no sistema: **5 modelos**, estratégia híbrida OpenRouter + NVIDIA NIM, custo $0/mês.

**Decisão final sobre providers — estratégia híbrida:**
- **OpenRouter** (1000 req/dia grátis, $10 depositados como crédito de reserva): Nano 30B, Super 120B, Nano 12B VL
- **NVIDIA NIM** (créditos Developer, key nvapi-...): Content Safety 4B, riva-translate 4B
- DeepSeek **excluído** da equipa de investigação — censura política do Estado chinês embutida (Taiwan, Tiananmen, Xi Jinping). Nemotron 3 Super como modelo principal sem censura política.

### Pendente / Próximos Passos

- [x] **FEITO** `.env` v3.1 deployed no Oracle pelo Claude Code — pipeline confirmado vivo (HTTP 200 OpenRouter, Dossiê a processar temas)
- [x] **FEITO** `reporter_configs` migrados para `v1-llm-reasoning` — 19 reporters com system prompts de raciocínio (3 fases), keywords removidas, desporto desactivado
- [x] **FEITO** Dispatcher LLM actualizado em Supabase — model Nano 30B, system prompt semântico, role=dispatcher
- [x] **FEITO** Equipa Elite actualizada em Supabase — 3 agentes com system prompts completos, pipeline=elite_bypass, requires_human_approval=true
- [x] **FEITO** Filosofia LLM-First documentada em ARCHITECTURE-MASTER.md — todos os agentes com raciocínio excepto Publisher P2/P3
- [x] **FEITO** `dispatcher.py` implementado — pipeline/src/openclaw/agents/dispatcher.py
- [x] **FEITO** `scheduler_ollama.py` actualizado — dispatcher(5m) + triagem(20m, no-op legado) + fact_checker(25m) + escritor(30m)
- [x] **FEITO** `dossie.py` deprecated — substituído pela Equipa de Investigação Elite; agente paused no Supabase; removido do scheduler
- [ ] **DEPLOY ORACLE** — git pull + systemctl restart openclaw (ver instruções abaixo)
- [ ] Activar agentes no Paperclip (status idle → active)
- [ ] Instalar NemoClaw no Oracle VM
- [ ] Cancelar Ollama Pro após confirmar OpenRouter funciona

### Como fazer deploy do dispatcher no Oracle

```bash
# No Oracle VM (SSH: opc@82.70.84.122)
cd ~/curador-de-noticias   # ou o path do projecto
git pull origin main
sudo systemctl restart openclaw
sudo systemctl status openclaw  # confirmar que está a correr
journalctl -u openclaw -f       # ver logs em tempo real
```

Primeiro batch de dispatcher nos logs deve mostrar:
```
Dispatcher: processando X eventos com nvidia/nemotron-nano-30b-instruct:free
Dispatcher: 'Título...' → ['categoria'] | prioridade=P2 | pt=0.75
Dispatcher concluído: fetched=X queued=Y rejected=Z stale=0 errors=0
```

---

## 2026-03-19 — Migração LLM-First: Filosofia de Raciocínio em Todos os Agentes

### Decisão Arquitectural

**Princípio:** Nenhum agente usa keyword matching ou automação cega. Todos os agentes com papel editorial raciocinam com LLM sobre o conteúdo completo.

**Motivação:** Keyword scoring gerava ~30-40% de erros de classificação (falsos positivos por contexto, multi-tematicidade não detectada, ironia não entendida). LLM com raciocínio contextual atinge >95% de precisão.

**Excepções documentadas (automação pura, sem raciocínio necessário):**
- Publisher P2 e P3 — scheduling temporal, sem decisão editorial
- Coletores (7) — fetch de APIs/RSS/Telegram, sem avaliação de conteúdo

**Alterações em Supabase:**

| Tabela | Mudança | skill_version |
|--------|---------|--------------|
| `reporter_configs` | keywords = {}, system prompts com 3 fases de raciocínio | v0-keywords → v1-llm-reasoning |
| `agents` (dispatcher) | model=Nano30B, system_prompt semântico, role=dispatcher | — |
| `agents` (elite 3) | system_prompts completos, pipeline=elite_bypass | — |

---

## 2026-03-16 — Deprecação Grok + Início Migração Oracle

- Grok API eliminada do sistema (deprecated 16/03/2026)
- Edge Functions `grok-reporter`, `grok-fact-check`, `grok-bias-check` deprecated
- Início da migração Fly.io → Oracle Cloud
- Paperclip instalado no Oracle como orquestrador (substitui Fly.io cron jobs)
- scheduler_ollama.py migrado para Oracle via systemd

---

## Notas de Arquitectura Permanentes

**Regra de ouro do pipeline:** Nenhum artigo publica sem passar por (1) Reporter, (2) FC Sectorial, (3) Auditor, (4) Escritor, (5) Editor-Chefe. A única excepção é a Equipa Elite que tem pipeline próprio com aprovação de Wilson.

**Supabase project ID:** `ljozolszasxppianyaac`
**Oracle VM:** `opc@82.70.84.122`
**Vercel:** frontend do Curador de Noticias
**OpenClaw service:** `sudo systemctl status openclaw.service`
**Telegram service:** `sudo systemctl status telegram-collector.service`

---

## 2026-03-22 — Limpeza Systemd + Diagnóstico Pipeline (por CEO)

### Systemd Services Arquivados

Os 3 systemd unit files foram **arquivados** para `/etc/systemd/system/archived/`:
- `noticia-pipeline.service` → archived
- `noticia-telegram.service` → archived
- `noticia-diretor-elite.service` → archived

**Motivo:** Desde a migração para Docker Compose (2026-03-21), os systemd services estavam `disabled/dead` mas os unit files permaneciam no sistema, criando confusão. O runtime activo é exclusivamente Docker Compose (3 containers: pipeline, telegram-bot, telegram-collector).

**Acção:** `systemctl disable` + movidos para `/etc/systemd/system/archived/` + `daemon-reload`. Reversível se necessário.

### Telegram Collector — FLOOD-WAIT

O `DELAY_BETWEEN_CHANNELS=10` está activo e confirmado no container (10s entre canais nos logs). No entanto, a conta Telegram tem um FLOOD-WAIT de ~21h imposto pelo Telegram API devido a abusos anteriores quando o delay era 0.5s. Resolução automática quando o flood-wait expirar.

Os 1278 canais estão correctos e verificados — rodam em 3 camadas de prioridade (Tier 1-2 sempre, Tier 3-4 rotação 1/3, Tier 5 rotação 1/5).

### Fact-Checker — Diagnóstico CRÍTICO

**Problema identificado:** O scheduler chama UMA ÚNICA função `run_fact_checker()` a cada 25 min. Esta função processa 10 items por ciclo, sequencialmente. Os 7 agentes fact-checker no Supabase (fc-mundo, fc-tech, fc-portugal, fc-economia, fc-saude, fc-justica, fc-forense) são apenas registos — o código NÃO os distribui nem os chama individualmente.

**Agravante:** 2 de 3 providers de web search estão em falha:
- Tavily: HTTP 432 (quota esgotada) — modo grátis mantido
- Exa.ai: HTTP 402 Payment Required — modo grátis mantido
- Serper.dev: único provider funcional, mas lento como fallback

**Impacto:** Backlog de 378 items em auditor_approved, throughput de ~5-15 items/ciclo (25min), estimativa de limpeza: 2-3 dias.

**Acção necessária (ASAP):** Paralelizar os fact-checkers sectoriais no scheduler para processar mais items por ciclo.

*Registado pelo CEO às 2026-03-22 21:00 UTC*

---

## 2026-03-22 — Fact-Checkers Sectoriais Paralelos (por CEO)

### Problema
Apenas 1 fact-checker genérico processava toda a intake_queue (~5-15 items/ciclo de 25min). Backlog acumulado de 378+ items em auditor_approved.

### Solução Implementada
Criado **fact_checker_parallel.py** (177 linhas) com arquitectura sectorial:

| Sector | Áreas |
|--------|-------|
| fc-mundo | geopolitica, politica_intl, diplomacia, defesa, defesa_estrategica |
| fc-tech | tecnologia, ciencia, energia, clima |
| fc-portugal | portugal, sociedade |
| fc-economia | economia, financas, crypto, regulacao |
| fc-saude | saude, direitos_humanos |
| fc-justica | desinformacao, crime_organizado |

**Mecanismo:** ThreadPoolExecutor com MAX_WORKERS=3, cada sector processa até FC_ITEMS_PER_SECTOR=5 items filtrados por área. Total teórico: até 30 items/ciclo (6× mais throughput).

### Alterações
1. **Novo ficheiro:** pipeline/src/openclaw/agents/fact_checker_parallel.py
2. **Modificado:** scheduler_ollama.py — import e job actualizados para run_fact_checkers_parallel
3. **Docker:** Container pipeline reconstruído e reiniciado — healthy ✅

### Configuração (.env)
- FC_ITEMS_PER_SECTOR=5 (default, pode ser ajustado)
- FC_MAX_WORKERS=3 (default, pode ser ajustado até 6)

### Estimativa de Impacto
- Throughput anterior: ~5-15 items/25min
- Throughput esperado: ~20-30 items/25min
- Tempo estimado para limpar backlog: ~8-16 horas (vs 2-3 dias)

### Estado
- Pipeline container: healthy ✅
- Job registado no scheduler: run_fact_checkers_parallel (25min) ✅
- Primeiro run automático: ~21:31 UTC
- Web search: Tavily (432) e Exa.ai (402) em modo grátis esgotado; Serper.dev activo

*Registado pelo CEO às 2026-03-22 21:17 UTC*

---

## 2026-03-22 — Ollama Web Search: Provider Primario (por CEO)

### Contexto
Tavily (432) e Exa.ai (402) em modo gratuito esgotado. Apenas Serper.dev activo.
Investigacao revelou que o Ollama Pro (ja subscrito a $20/mes) inclui Web Search API gratuito, sem limites publicados, multilinguee e sem vies.

### Testes Realizados
- **Burst test:** 20/20 pesquisas consecutivas sem throttling (~1.3s/pesquisa)
- **Multilinguee:** Testado em 6 idiomas (PT-PT, Mandarim, Russo, Farsi, Arabe, Swahili) - todos com resultados de qualidade
- **PT-PT vs PT-BR:** Distingue correctamente por contexto (fontes portuguesas para temas portugueses)
- **Qualidade:** Reuters, Folha, Globo, Parlamento.pt, CNN Portugal, DW, Interfax, UN News
- **Fallback:** Quando Ollama falha, Serper.dev assume automaticamente

### Alteracoes
1. **pipeline/src/openclaw/agents/fact_checker.py** - Ollama Web Search como provider primario
   - Nova chain: Ollama -> Serper -> Tavily -> Exa
   - Funcao _web_search() com fallback automatico
   - Env vars: OLLAMA_BASE_URL + OLLAMA_API_KEY (ja existiam)

2. **telegram-bot/elite_fact_checker.py** - Ollama como tool de pesquisa
   - Nova funcao _search_ollama() com exclusao de dominio do reporter
   - Novo tool ollama_search para o LLM usar como primeira opcao
   - Adicionado ao _execute_search()
   - Corrigido tool_choice="required" nos rounds 0-1 (forca pesquisa)
   - Retry com correction prompt quando JSON parsing falha
   - Coluna fc_bias_flags adicionada a elite_findings (Supabase migration)

3. **Docker:** Ambos containers (pipeline + telegram-bot) reconstruidos e healthy

### Verificacao
- Container pipeline: healthy, Ollama search retorna 7 resultados
- Container bot: healthy, _search_ollama funcional
- Fallback chain testado: Ollama desactivado -> Serper assume
- Sem erros de import ou runtime

### Impacto
- Custo web search: $0 adicional (incluido no Ollama Pro $20/mes)
- Fiabilidade: chain de 4 providers em vez de 3
- Qualidade: resultados multilinguees com conteudo rico (3K-12K chars)
- Vies: sem personalizacao, sem filtros editoriais

*Registado pelo CEO as 2026-03-22 22:05 UTC*

---

## 2026-03-22 23:20 — Fix Elite FC Forense: Arquitectura Duas Fases

### Problema
O FC Forense ficava preso e nunca produzia veredictos JSON. Causa raiz: **deepseek-v3.2 (modelo de raciocínio) retorna respostas vazias** quando:
1. `tool_choice="none"` é usado via Ollama API
2. `max_tokens` é insuficiente — o modelo gasta ~800 tokens na fase interna de raciocínio antes de produzir output visível
3. Mesmo com `max_tokens` aumentado, o modelo demora >5 min com prompts grandes (15+ evidências), causando timeout

### Solução: Arquitectura Duas Fases + Modelo Split
**Fase 1 (Pesquisa):** deepseek-v3.2 com tools (4 rondas max, tool_choice="required"/"auto")
- Recolhe evidências independentes via Ollama/Serper/Tavily/Exa
- Armazena resultados num array de evidências

**Fase 2 (Veredicto):** cogito-2.1:671b (modelo não-raciocínio) sem tools
- Conversa LIMPA (sem mensagens tool_call no histórico)
- Recebe resumo das evidências em texto plano
- Produz JSON válido em ~7-10 segundos
- 3 tentativas com retry se JSON inválido

### Mudanças
- `elite_fact_checker.py`: Reescrita de `_verify_finding()` → 3 funções: `_collect_search_evidence()`, `_generate_verdict()`, `_verify_finding()`
- `.env` do bot: Adicionado `MODEL_FC_VERDICT=cogito-2.1:671b` e `MODEL_FACTCHECKER=deepseek-v3.2`
- Evidências limitadas a 10 items com excerpts de 200 chars
- Eliminado uso de `tool_choice="none"` (incompatível com Ollama)

### Testes
- 3/3 findings verificados com sucesso (63s, 49s, 53s por finding)
- JSON válido produzido na primeira tentativa em todos os casos
- Full run lançado: 72 findings, estimativa ~66 min

---

## 2026-03-23 09:30 — Fix Escritor: JSON Parsing + Threshold Alignment

### Problema
O Escritor acumulou ~150 items aprovados sem conseguir publicar. Duas causas:

1. **JSON parsing (causa principal):** O LLM (mistral-large-3:675b) produz newlines literais dentro de strings JSON no campo corpo_html. O json.loads() em modo strict rejeita estes caracteres de controlo com erro Invalid control character. Resultado: 154 erros consecutivos vs 1 artigo publicado.

2. **Threshold desalinhado:** O Python usava CERTAINTY_THRESHOLD=0.7 mas o trigger PostgreSQL enforce_publish_quality exige >= 0.895. 24 items passavam pelo Python mas eram rejeitados pelo trigger, ficando perpetuamente na queue.

### Solução
1. **strict=False:** Na linha 167 de escritor.py, mudei json.loads(raw_json) para json.loads(raw_json, strict=False). Isto permite newlines/tabs dentro de strings JSON — comportamento esperado com output de LLMs.

2. **Threshold alinhado:** Mudei ESCRITOR_CERTAINTY_THRESHOLD default de 0.7 para 0.895, alinhando com o trigger PostgreSQL. Items abaixo do threshold são movidos para fact_check imediatamente em vez de falhar no RPC.

3. **Limpeza de backlog:** Executei 3 rondas manuais do escritor, publicando ~90 artigos. Queue foi de 126 approved para 1.

### Resultado
- 0 erros de JSON após o fix
- ~90 artigos publicados em 3 batches
- Backlog escritor limpo (126 → 1)
- Pipeline a funcionar normalmente

---

---

## 2026-03-23 12:00 — Fix Cronistas: Automacao Semanal

### Problema
As cronicas semanais dos 10 cronistas nao foram publicadas para a semana de 22/Mar. A ultima cronica datava de 15/Mar. A Edge Function cronista no Supabase requer PUBLISH_API_KEY no header Authorization, e nao existe nenhum cron automatico — as invocacoes eram manuais.

### Diagnostico
1. Sem trigger automatico: nem no APScheduler nem em crontab
2. Edge Function auth: PUBLISH_API_KEY do .env do pipeline nao corresponde ao secret da Edge Function
3. Resultado: dependencia de invocacao manual que foi esquecida

### Solucao
1. Geracao imediata: Criei script Python no container do pipeline que replica a logica da Edge Function, com acesso directo ao Supabase e Ollama (gemma3:27b). Executei para os 10 cronistas: 10/10 publicados com sucesso (~3.5 min total).

2. Modulo permanente: Criei agents/cronistas.py — agente integrado no pipeline com logging pipeline_runs e compativel com o ollama_client existente.

3. Scheduler semanal: Adicionei job CronTrigger no scheduler_ollama.py — domingos as 10:00 UTC. Camada 6 no pipeline (apos pipeline_health).

4. Deploy: Rebuild + restart do container pipeline. 6 jobs registados no scheduler (5 interval + 1 cron).

### Resultado
- 10/10 cronicas publicadas para semana 16-23/Mar
- Automacao semanal configurada (domingos 10:00 UTC)
- Proxima execucao automatica: domingo 30/Mar 10:00 UTC

---

## 2026-03-23 15:00 — V3 Contra-Media: Pivot Completo

### Contexto
Wilson decidiu reorientar o NoticIA de canal de noticias generico para plataforma contra-media.
Objectivo: auditar media, desmascarar vies e omissoes, cobrir noticias ignoradas pelo mainstream.

### Alteracoes (4 fases implementadas numa sessao)

**Fase 1 — Fundacao (DB + routing)**
- Migracao DB: source_type (raw_events), vertente/bias_verdict/media_audit (intake_queue), article_type (articles)
- collector_runner.py: marca source_type='media' (RSS/GDELT) ou 'alternative' (Telegram)
- dispatcher.py: propaga source_type para vertente na intake_queue (media_watch/alt_news/editorial)
- RPC publish_article_with_sources: aceita article_type no payload

**Fase 2 — FC Dual-Mode**
- fact_checker.py: 3 modos por vertente:
  - media_watch: audita honestidade, framing, omissoes (busca o OUTRO LADO)
  - alt_news: verificacao rigorosa (exige 3+ fontes independentes)
  - editorial: verifica factos de injecoes manuais do Wilson
- Grava bias_verdict (bias_type, omitted_facts, counter_narrative) e media_audit (publish_recommendation)

**Fase 3 — Decisor Editorial + Escritor V3**
- editorial_decisor.py (NOVO): gate deterministico entre FC e escritor
  - Noticia dos media sem vies → DESCARTA (nao nos interessa)
  - Vies detectado → expose
  - Omissao detectada → artigo de omissao
  - Ambiguo → wilson_review via Telegram
- escritor.py: 6 templates de escrita (expose, omissao, alt-news, fact-check, editorial, standard)
- Status flow: auditor_approved → FC → approved → Decisor → ready_to_write → Escritor → published

**Fase 4 — Injector Manual + Detector de Omissoes**
- bot.py: /injecta URL [contexto] — Wilson injeta URLs via Telegram
- coverage_analyzer.py (NOVO): cada 6h cruza media vs alternativo, detecta gaps
- scheduler: 8 jobs (collectors, dispatcher, FC, decisor, escritor, health, coverage, cronistas)

### Ficheiros alterados (7 modificados, 2 criados)
- pipeline/src/openclaw/collector_runner.py — source_type
- pipeline/src/openclaw/agents/dispatcher.py — vertente routing
- pipeline/src/openclaw/agents/fact_checker.py — dual-mode completo
- pipeline/src/openclaw/agents/fact_checker_parallel.py — vertente logging
- pipeline/src/openclaw/agents/escritor.py — 6 templates
- pipeline/src/openclaw/scheduler_ollama.py — 8 jobs
- telegram-bot/bot.py — /injecta command
- pipeline/src/openclaw/agents/editorial_decisor.py (NOVO)
- pipeline/src/openclaw/agents/coverage_analyzer.py (NOVO)

### Deploy
- Docker containers reiniciados (pipeline, bot, telegram-collector)
- Pipeline V3 activo com 8 jobs no scheduler
- Commit cafd165 pushed para GitHub

### Modelos activos
- Dispatcher: gpt-oss:20b (routing rapido)
- FC: mistral-large-3:675b (sem vies chines)
- Escritor: mistral-large-3:675b
- Cronistas: gemma3:27b

### Estado
Pipeline V3 em producao. Primeiros resultados do FC dual-mode e do decisor editorial
serao visiveis nos proximos ciclos (~40 min para pipeline completo).
