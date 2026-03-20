# SOTA SKILLS — Claude Root Configuration (NoticIA Edition)

> Este ficheiro e o cerebro central. Define fases, classificacao, routing automatico e regras de prioridade.
> Customizado para o projecto NoticIA — curadoria automatizada de noticias em PT-PT.

---

## 1. REGRAS FUNDAMENTAIS

### Prioridade (Tier 1 — Inviolavel)
1. **Nunca inventar dados** — se nao sabes, pergunta ou pesquisa
2. **Nunca apagar codigo sem confirmar** — propoe a mudanca, espera aprovacao
3. **Fase 0 esta SEMPRE ativa** — skills essenciais sao aplicadas em TODAS as respostas
4. **Profession news-curator esta SEMPRE ativa** — este e um projecto de curadoria de noticias
5. **Seguir o ARCHITECTURE.md** — e o mapa oficial de skills e fases
6. **Convencoes do projeto prevalecem** — Python para pipeline, TypeScript para frontend
7. **Verificar antes de declarar "done"** — evidencia fresca obrigatoria (verification-before-completion)
8. **Skills sao lei, nao sugestao** — 1% de chance de aplicar = invocacao obrigatoria (enforcement-layer)
9. **PT-PT obrigatorio** — Artigos e outputs editoriais sempre em Portugues Europeu, nunca PT-BR

### Prioridade (Tier 2 — Forte)
1. Manter codigo limpo e tipado (Python type hints / TypeScript strict)
2. Commits atomicos e convencionais
3. Testar antes de deployar
4. Documentar decisoes arquiteturais
5. `.env` e a fonte de verdade para modelos — nunca hardcodar

### Prioridade (Tier 3 — Preferencial)
1. Preferir composicao sobre heranca
2. Preferir server components por defeito (Next.js frontend)
3. Preferir pre-filtragem deterministica sobre LLM (pipeline)
4. Preferir batch LLM sobre chamadas individuais
5. Preferir fallback gracioso sobre crash (eventos voltam ao pool)

---

## 2. CLASSIFICADOR DE REQUESTS

Quando recebes um pedido do utilizador, classifica-o automaticamente:

```
REQUEST → [Classificar Tipo] → [Identificar Fase] → [Selecionar Skills] → [Executar]
```

### Tipos de Request

| Tipo | Descricao | Fases Tipicas |
|------|-----------|---------------|
| `IDEA` | Ideia vaga, brainstorm, "quero fazer X" | 1 |
| `PLAN` | Planear arquitetura, escolher stack | 1, 2 |
| `BUILD` | Implementar feature, criar componente | 2, 3, 4 |
| `FIX` | Bug, erro, problema de performance | 0, 3, 4, 5 |
| `TEST` | Escrever testes, auditar codigo | 5 |
| `DEPLOY` | Deployar, CI/CD, systemd | 6 |
| `REFACTOR` | Melhorar codigo existente sem mudar comportamento | 0, 3, 4, 5 |
| `REVIEW` | Code review, PR review, audit | 5, 6 |
| `ADAPT` | Adicionar/remover/alterar funcionalidade mid-project | Depende |
| `EDITORIAL` | Ajustar pipeline editorial, modelos, prompts, classificacao | 0, 3 + news-curator |

---

## 3. ROUTER AUTOMATICO

### Logica de Routing

```
1. ENFORCEMENT CHECK: Verificar se alguma skill se aplica (1% chance = obrigatorio)
2. SEMPRE ativar: Fase 0 (8 skills essenciais — ver lista abaixo)
3. SEMPRE ativar: Profession news-curator
4. Classificar o request (ver tabela acima)
5. Identificar a(s) fase(s) relevante(s)
6. Dentro de cada fase, selecionar skills por keywords (ver ARCHITECTURE.md)
7. Aplicar as skills selecionadas
8. VERIFICATION GATE: Antes de declarar "done", evidencia fresca obrigatoria
```

### Routing por Keywords

| Keywords no Pedido | Skills Ativadas |
|-------------------|-----------------|
| ideia, brainstorm, mvp, conceito | brainstorming, product-manager-toolkit |
| concorrencia, mercado, alternativas | competitive-landscape |
| decisao tecnica, ADR, tradeoff | architecture-decision-records |
| arquitetura, sistema, design pattern | senior-architect, architecture-patterns |
| base de dados, schema, ORM, SQL, Supabase | database-design, **news-curator** |
| API, REST, GraphQL, tRPC, endpoint | api-patterns |
| backend, servidor, Node, Express, Python, pipeline | backend-dev-guidelines, senior-fullstack, **news-curator** |
| seguranca API, rate limit, CORS | api-security-best-practices |
| auth, login, JWT, OAuth, sessao | auth-implementation-patterns |
| frontend, React, Next.js, componente | frontend-developer, react-best-practices |
| design, UI, layout, cores, tipografia | frontend-design, ui-ux-pro-max |
| Tailwind, CSS, estilo, classe | tailwind-patterns |
| teste, TDD, unit test, coverage | test-driven-development |
| review, PR, checklist | code-review-checklist |
| seguranca, auditoria, vulnerabilidade | security-auditor |
| qualidade, audit, score | vibe-code-auditor |
| performance, lento, otimizar, Core Web Vitals, tokens, batch | performance-engineer, **news-curator** |
| e2e, Playwright, Cypress, integracao | e2e-testing-patterns |
| Docker, container, imagem | docker-expert |
| deploy, producao, rollout, CI/CD, systemd, Oracle | deployment-procedures |
| commit, mensagem commit | commit |
| PR, pull request, merge | create-pr |
| changelog, release notes, versao | changelog-automation |
| done, completo, pronto, terminado, feito | verification-before-completion |
| paralelo, agentes, concurrent, dispatch | dispatching-parallel-agents |
| agente, agent, autonomo, pipeline, orchestration, LLM, MCP | sota-agent-engineering, **news-curator** |
| noticia, artigo, editorial, facto, PT-PT | **news-curator** |
| dispatcher, fact-checker, escritor, collector | **news-curator**, sota-agent-engineering |
| curadoria, triagem, classificacao, dedup | **news-curator**, performance-engineer |
| Ollama, modelo, batch, tokens, quality gate | **news-curator**, sota-agent-engineering |
| Supabase, intake_queue, raw_events, articles | **news-curator**, database-design |
| Telegram, bot, Diretor Elite | **news-curator** |

---

## 4. GESTAO DE FASES

### Fase 0 — Essenciais (SEMPRE ATIVAS)
Skills que se aplicam a TODAS as interacoes, independentemente do contexto.

- **concise-planning**: Comecar com plano antes de executar
- **systematic-debugging**: Debug metodologico quando ha erros
- **lint-and-validate**: Validar codigo antes de entregar
- **git-pushing**: Guardar trabalho com seguranca
- **kaizen**: Melhoria continua — sugerir melhorias quando relevante
- **verification-before-completion**: Gate obrigatorio antes de declarar "done"
- **dispatching-parallel-agents**: Orquestracao de sub-agentes em paralelo
- **enforcement-layer**: Garante invocacao obrigatoria de skills relevantes

### Profession — News Curator (SEMPRE ATIVA)
Skill de profissao que se aplica a TODAS as interacoes neste projecto.

- **news-curator**: Curadoria de noticias, padroes editoriais, PT-PT, pipeline jornalistico, gestao de agentes

### Fase 1 — Ideacao & Planeamento
Ativada quando o utilizador esta a explorar ideias ou planear.

### Fase 2 — Arquitetura & Design
Ativada quando se esta a definir a estrutura do sistema.

### Fase 3 — Backend
Ativada durante implementacao de logica servidor (Python pipeline ou Node.js).

### Fase 4 — Frontend & UI
Ativada durante implementacao de interfaces (Next.js + Tailwind).

### Fase 5 — Qualidade & Auditoria
Ativada para testes, reviews, e auditoria.

### Fase 6 — Deploy & Manutencao
Ativada para deployment (systemd, Oracle VM) e operacoes.

---

## 5. ADAPTABILIDADE MID-PROJECT

Quando o utilizador pede mudancas a meio do projeto:

### Protocolo ADAPT

1. **Analisar** — O que muda? (requisitos, stack, funcionalidade)
2. **Classificar** — Em que fase cai a mudanca?
3. **Planear** — Que skills ativar para a mudanca?
4. **Impacto** — Que partes existentes sao afetadas?
5. **Executar** — Implementar com as skills corretas
6. **Validar** — Correr testes e lint para garantir que nada partiu

### Exemplos de Adaptacao (NoticIA)

| Pedido | Acao |
|--------|------|
| "Adiciona novo collector" | Ativa news-curator + backend-dev-guidelines (F3) |
| "Muda o modelo do escritor" | Ativa news-curator + sota-agent-engineering (F2) |
| "Optimiza o pipeline" | Ativa news-curator + performance-engineer (F5) + sota-agent-engineering (F2) |
| "Adiciona testes ao dispatcher" | Ativa test-driven-development (F5) + news-curator |
| "Deploy nova versao" | Ativa deployment-procedures (F6) + verification-before-completion |
| "Melhora o fact-checking" | Ativa news-curator + backend-dev-guidelines (F3) |
| "Adiciona novo agente" | Ativa news-curator + sota-agent-engineering (F2) + database-design (F2) |
| "Frontend: nova pagina de artigo" | Ativa frontend-developer (F4) + react-best-practices (F4) + news-curator |

---

## 6. EXTENSIBILIDADE — PROFESSIONS

Skills de profissao vivem em `professions/` e sao geridas pelo utilizador.
Formato identico as skills normais (`SKILL.md` com frontmatter YAML).

**Profession ativa neste projecto:**
- `professions/news-curator/SKILL.md` — Curadoria de noticias AI (SEMPRE ATIVA)

Para ativar uma profession skill adicional:
1. O utilizador menciona o contexto profissional
2. O router deteta keywords da profissao
3. A skill de profissao e combinada com as skills tecnicas relevantes

---

## 7. WORKFLOWS (SLASH COMMANDS)

Workflows sao sequencias pre-definidas de skills. Vivem em `workflows/`.

| Workflow | Descricao | Skills Encadeadas |
|----------|-----------|-------------------|
| `/brainstorm` | Da ideia ao plano | brainstorming → product-manager-toolkit → architecture-decision-records |
| `/plan` | Do plano a arquitetura | concise-planning → senior-architect → architecture-patterns → database-design |
| `/debug` | Debug sistematico | systematic-debugging → lint-and-validate → test-driven-development |
| `/pipeline` | Audit do pipeline NoticIA | news-curator → performance-engineer → vibe-code-auditor → verification-before-completion |

---

## 8. FORMATO DE RESPOSTA

Quando ativas skills, segue este formato mental (nao precisas mostrar ao utilizador):

```
[Interno]
Request: "..."
Tipo: BUILD
Fases: 0, 3, Profession
Skills ativas: concise-planning, news-curator, backend-dev-guidelines, sota-agent-engineering
```

Depois responde normalmente, aplicando o conhecimento das skills ativas.

---

*Este ficheiro e lido automaticamente pelo Claude. Nao e necessario referencia-lo manualmente.*
