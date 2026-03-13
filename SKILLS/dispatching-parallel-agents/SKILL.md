---
name: Dispatching Parallel Agents
description: Protocolo para orquestrar sub-agentes em paralelo quando existem problemas independentes.
phase: 0
always_active: true
---

# Dispatching Parallel Agents

## Core Principle

**Despacha um agente por dominio independente. Deixa-os trabalhar em concorrencia.**

Trabalho sequencial quando os problemas sao independentes e desperdicio. Se tres subsistemas estao partidos por razoes diferentes, lanca tres agentes — nao resolvas um de cada vez.

---

## Decision Framework

### QUANDO Usar Agentes Paralelos

Usa quando TODAS estas condicoes se verificam:

- [ ] **3+ problemas** com causas raiz distintas
- [ ] **Subsistemas independentes** — cada problema pode ser resolvido sem informacao dos outros
- [ ] **Sem estado partilhado** — agentes nao interferem entre si
- [ ] **Scope claro** — cada problema tem fronteiras bem definidas

### QUANDO NAO Usar

Evita quando QUALQUER destas se aplica:

- [ ] Falhas **interligadas** — um problema causa outro
- [ ] Necessidade de **compreensao global** do sistema
- [ ] Agentes **interfeririam** no trabalho uns dos outros (mesmos ficheiros)
- [ ] Problema **unico** que requer investigacao sequencial
- [ ] Alteracoes que afetam **estado partilhado** (ex: schema DB que afeta multiplos componentes)

---

## Processo de Dispatch — 4 Passos

### Passo 1: Identificar Dominios Independentes

Agrupa os problemas por componente/subsistema:

```
Exemplo — 4 falhas no Curador de Noticias:

Dominio A: Edge Function `receive-article` retorna 500
Dominio B: Componente ArticleCard nao renderiza tags
Dominio C: Migration falha em coluna nullable
Dominio D: CSS do Header quebrado em mobile

→ Dominios A, B, C, D sao independentes
→ Despachar 4 agentes
```

### Passo 2: Criar Tarefas Focadas

Cada tarefa de agente DEVE ter:

1. **Scope especifico** — um dominio, um problema
2. **Contexto necessario** — ficheiros relevantes, erro exacto, comportamento esperado
3. **Constraints** — que ficheiros pode alterar, que NAO pode tocar
4. **Deliverable claro** — o que constitui "resolvido"

```
Template:
---
Dominio: [nome do subsistema]
Problema: [descricao exacta do erro/bug]
Ficheiros relevantes: [lista de paths]
Constraints: NAO alterar [ficheiros fora do scope]
Deliverable: [condicao de sucesso verificavel]
---
```

### Passo 3: Despachar Concorrentemente

- Lancar TODOS os agentes **simultaneamente**, nao sequencialmente
- Cada agente recebe APENAS o contexto do seu dominio
- Usar o Agent tool com prompts focados
- Marcar como background se nao bloqueiam o trabalho principal

### Passo 4: Review & Integrate

Quando os agentes terminam:

1. **Examinar resultados** — Ler o resumo de cada agente
2. **Verificar conflitos** — Algum agente alterou ficheiros fora do seu scope?
3. **Correr test suite completa** — `npm run build` + testes apos integrar TODAS as mudancas
4. **Verificar independencia** — Se um agente falhou, os outros devem funcionar independentemente

---

## Exemplos no Contexto do Curador de Noticias

### Cenario 1: Multiplas Edge Functions com Bugs

```
Agente 1 → Fix receive-article (Deno runtime)
Agente 2 → Fix receive-claims (validation logic)
Agente 3 → Fix agent-log (schema mismatch)
→ Independentes: cada funcao tem o seu ficheiro e endpoint
```

### Cenario 2: Multiplos Componentes UI Partidos

```
Agente 1 → Fix Header responsividade
Agente 2 → Fix ArticleCard rendering
Agente 3 → Fix Dashboard charts
→ Independentes: componentes isolados, sem estado partilhado
```

### Cenario 3: NAO Paralelizar

```
Bug: ArticleCard mostra dados errados
Causa: Schema DB mudou → API retorna formato diferente → Component espera formato antigo
→ SEQUENCIAL: fix schema → fix API → fix component
→ Cada passo depende do anterior
```

---

## Anti-Patterns

| Anti-Pattern | Porque e Mau | Correcao |
|-------------|-------------|----------|
| Despachar agente para problema dependente | Agente vai falhar ou fazer fix parcial | Resolver sequencialmente |
| Dar contexto global a cada agente | Agente fica confuso, scope inflado | Dar APENAS contexto do dominio |
| Nao verificar conflitos | Agentes podem alterar o mesmo ficheiro | Review cruzado obrigatorio |
| Skip test suite apos integrar | Conflitos silenciosos passam | Build + testes completos obrigatorios |
| Despachar 1 agente | Overhead desnecessario para problema unico | Resolver directamente |

---

## Principios

1. **Independencia e pre-requisito** — Nunca paralelizar problemas dependentes
2. **Contexto minimo** — Cada agente recebe apenas o que precisa
3. **Verificacao pos-integracao** — Test suite completa apos merge de resultados
4. **Falha isolada** — Se um agente falha, os outros nao sao afetados
5. **Concorrencia real** — Lancar simultaneamente, nao sequencialmente
