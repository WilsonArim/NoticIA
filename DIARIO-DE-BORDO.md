# Diário de Bordo — Curador de Noticias

> Registo cronológico das decisões, migrações e marcos do projecto.
> Actualizar no início de cada sessão de trabalho significativa.

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
