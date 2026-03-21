# ARCHITECTURE — Mapa de Skills, Fases & Routing (NoticIA Edition)

> Referencia completa de todas as skills, organizacao por fases, e matriz de routing.
> Customizado para o projecto NoticIA — curadoria automatizada de noticias em PT-PT.

---

## Visao Geral

```
Total de Skills: 45 + 1 Profession (37 core + 8 security)
Fases: 7 (0-6)
Skills Fase 0 (sempre ativas): 9 (8 core + secrets-management)
Skills sob demanda: 36
Professions: 1 (news-curator — SEMPRE ATIVA)
Workflows: 6 (3 core + 3 security)
Security Framework: SECURITY/ (8 skills + SECURITY.md)
```

---

## Mapa Completo de Skills

### FASE 0 — Essenciais (SEMPRE ATIVAS)

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Concise Planning | `concise-planning/` | Plano estruturado antes de executar |
| Systematic Debugging | `systematic-debugging/` | Debug metodologico com hipoteses |
| Lint and Validate | `lint-and-validate/` | Validacao automatica de codigo |
| Git Pushing | `git-pushing/` | Commits seguros e convencionais |
| Kaizen | `kaizen/` | Melhoria continua, sugestoes proativas |
| Verification Before Completion | `verification-before-completion/` | Gate obrigatorio antes de declarar "done" |
| Dispatching Parallel Agents | `dispatching-parallel-agents/` | Orquestracao de sub-agentes em paralelo |
| Enforcement Layer | `enforcement-layer/` | Garante invocacao obrigatoria de skills |
| **Secrets Management** | **`SECURITY/secrets-management/`** | **Disciplina de segredos — SEMPRE ATIVA** |

### PROFESSION — News Curator (SEMPRE ATIVA)

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| News Curator | `professions/news-curator/` | Curadoria de noticias, editorial AI, pipeline jornalistico, PT-PT |

### FASE 1 — Ideacao & Planeamento

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Brainstorming | `brainstorming/` | De ideia vaga a plano concreto de MVP |
| Product Manager Toolkit | `product-manager-toolkit/` | PRD, priorizacao RICE, user stories |
| Competitive Landscape | `competitive-landscape/` | Analise de concorrencia e mercado |
| Architecture Decision Records | `architecture-decision-records/` | Documentar decisoes tecnicas (ADR) |

### FASE 2 — Arquitetura & Design de Sistema

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Senior Architect | `senior-architect/` | Arquitetura de software abrangente |
| Architecture Patterns | `architecture-patterns/` | Clean Architecture, DDD, Hexagonal |
| Database Design | `database-design/` | Schema design, normalizacao, ORM |
| API Patterns | `api-patterns/` | REST vs GraphQL vs tRPC |
| SOTA Agent Engineering | `sota-agent-engineering/` | Arquitectura de agentes autonomos SOTA |
| **Threat Modeling** | **`SECURITY/threat-modeling/`** | **STRIDE, attack surface, mitigacoes** |
| **Compliance & Privacy** | **`SECURITY/compliance-privacy/`** | **GDPR, RGPD, privacy-by-design** |

### FASE 3 — Backend

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Backend Dev Guidelines | `backend-dev-guidelines/` | Padroes Python/Node.js/TypeScript |
| Senior Fullstack | `senior-fullstack/` | Guia completo fullstack |
| API Security Best Practices | `api-security-best-practices/` | Seguranca de APIs |
| Auth Implementation Patterns | `auth-implementation-patterns/` | JWT, OAuth2, sessoes |

### FASE 4 — Frontend & UI

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Frontend Developer | `frontend-developer/` | React 19+ e Next.js 15+ |
| Frontend Design | `frontend-design/` | Diretrizes UI e estetica |
| UI/UX Pro Max | `ui-ux-pro-max/` | Design systems, tokens, layouts |
| React Best Practices | `react-best-practices/` | Performance React/Next.js |
| Tailwind Patterns | `tailwind-patterns/` | Tailwind CSS v4 |

### FASE 5 — Qualidade, Testes & Auditoria

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Test-Driven Development | `test-driven-development/` | TDD: Red, Green, Refactor |
| Code Review Checklist | `code-review-checklist/` | Checklist para PRs |
| Security Auditor | `security-auditor/` | Auditorias de seguranca |
| Vibe Code Auditor | `vibe-code-auditor/` | Qualidade com scoring deterministico |
| Performance Engineer | `performance-engineer/` | Otimizacao de performance |
| E2E Testing Patterns | `e2e-testing-patterns/` | Testes end-to-end fiaveis |
| **Supply Chain Security** | **`SECURITY/supply-chain-security/`** | **Dependencias, lockfiles, signed commits** |

### FASE 6 — Deploy & Manutencao

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Docker Expert | `docker-expert/` | Containers e multi-stage builds |
| Deployment Procedures | `deployment-procedures/` | Rollout seguro, CI/CD |
| Commit | `commit/` | Conventional commits |
| Create PR | `create-pr/` | PRs com contexto para review |
| Changelog Automation | `changelog-automation/` | Release notes consistentes |
| **Infrastructure Hardening** | **`SECURITY/infrastructure-hardening/`** | **SSH, firewall, TLS, fail2ban** |
| **DevSecOps Pipeline** | **`SECURITY/devsecops-pipeline/`** | **CI/CD seguro, SAST, scanning** |
| **Incident Response** | **`SECURITY/incident-response/`** | **Playbooks, post-mortem, recuperacao** |
| **Production Readiness** | **`SECURITY/production-readiness/`** | **Gate proativo: containerizacao, CI/CD, monitoring, backups — AUTO em DEPLOY** |

---

## Mapa de Seguranca

### Cobertura por Camada (Defense-in-Depth)

| Camada | Skill Responsavel | Fase |
|--------|-------------------|------|
| Segredos & Credenciais | **SECURITY/secrets-management** | 0 (SEMPRE ATIVA) |
| Modelacao de Ameacas | **SECURITY/threat-modeling** | 2 |
| Compliance & Privacidade | **SECURITY/compliance-privacy** | 2 |
| Cadeia de Fornecimento | **SECURITY/supply-chain-security** | 5 |
| Infraestrutura | **SECURITY/infrastructure-hardening** | 6 |
| Pipeline CI/CD | **SECURITY/devsecops-pipeline** | 6 |
| Resposta a Incidentes | **SECURITY/incident-response** | 6 |
| Production Readiness | **SECURITY/production-readiness** | **6 (AUTO em DEPLOY)** |

### Documento Mestre
`SECURITY/SECURITY.md` — Framework completo de defense-in-depth, Security-by-Default Checklist, e guia de integracao.

---

## Matriz de Routing

### Keywords → Skills

```
IDEACAO:
  ideia|brainstorm|mvp|conceito       → brainstorming, product-manager-toolkit
  concorrencia|mercado|alternativas   → competitive-landscape
  decisao|ADR|tradeoff                → architecture-decision-records

ARQUITETURA:
  arquitetura|sistema|pattern         → senior-architect, architecture-patterns
  database|schema|ORM|SQL|Prisma      → database-design
  API|REST|GraphQL|tRPC|endpoint      → api-patterns
  agente|agent|autonomo|pipeline|orchestration|MCP → sota-agent-engineering
  ameaca|threat|STRIDE|attack surface → SECURITY/threat-modeling
  GDPR|RGPD|privacidade|compliance   → SECURITY/compliance-privacy

BACKEND:
  backend|servidor|Node|Express|Python → backend-dev-guidelines, senior-fullstack
  seguranca-api|rate-limit|CORS       → api-security-best-practices
  auth|login|JWT|OAuth|sessao         → auth-implementation-patterns

FRONTEND:
  frontend|React|Next.js|componente   → frontend-developer, react-best-practices
  design|UI|layout|cores|tipografia   → frontend-design, ui-ux-pro-max
  Tailwind|CSS|estilo|classe          → tailwind-patterns

QUALIDADE:
  teste|TDD|unit|coverage             → test-driven-development
  review|PR|checklist                 → code-review-checklist
  seguranca|auditoria|vulnerabilidade → security-auditor
  qualidade|audit|score               → vibe-code-auditor
  performance|lento|otimizar|CWV      → performance-engineer
  e2e|Playwright|Cypress              → e2e-testing-patterns
  dependencia|lockfile|npm-audit|pip-audit → SECURITY/supply-chain-security

DEPLOY:
  Docker|container|imagem             → docker-expert
  deploy|producao|rollout|CI/CD       → deployment-procedures, **SECURITY/devsecops-pipeline**, **SECURITY/production-readiness (AUTO)**
  commit|mensagem                     → commit
  PR|pull-request|merge               → create-pr
  changelog|release|versao            → changelog-automation
  SSH|firewall|TLS|fail2ban|hardening → SECURITY/infrastructure-hardening
  incidente|breach|post-mortem|recuperacao → SECURITY/incident-response

SECURE (NOVO):
  segredo|secret|.env|API-key|token|credencial → SECURITY/secrets-management (SEMPRE ATIVA)
  security-audit|pentest|hardening    → SECURITY/infrastructure-hardening, security-auditor

ENFORCEMENT (SEMPRE ATIVO):
  done|completo|pronto|terminado|feito → verification-before-completion
  paralelo|agentes|concurrent|dispatch → dispatching-parallel-agents
  (enforcement-layer aplica-se automaticamente a TODOS os requests)

NOTICIA (SEMPRE ATIVO — Profession: news-curator):
  noticia|artigo|editorial|facto      → news-curator (profession)
  pipeline|dispatcher|fact-checker    → news-curator + sota-agent-engineering
  escritor|redacao|PT-PT|portugues    → news-curator
  curadoria|triagem|classificacao     → news-curator + sota-agent-engineering
  collector|RSS|GDELT|ACLED|Telegram  → news-curator
  Supabase|intake_queue|raw_events    → news-curator + database-design
  Ollama|modelo|LLM|batch            → news-curator + sota-agent-engineering
  dedup|title_hash|filtro             → news-curator + performance-engineer
  fact-check|verificacao|fonte        → news-curator
  publicacao|publish|artigo           → news-curator
```

### Complexidade → Combinacao de Skills

| Complexidade | Comportamento |
|-------------|---------------|
| Simples (1 ficheiro, 1 tarefa) | 1-2 skills da fase relevante + news-curator |
| Media (multiplos ficheiros, 1 feature) | 2-4 skills, possivelmente cross-fase + news-curator |
| Alta (sistema completo, multiplas features) | 4+ skills, multiplas fases em sequencia + news-curator |

---

## Fluxo de Ativacao

```
[Pedido do Utilizador]
       │
       ▼
[ENFORCEMENT CHECK]
  "Alguma skill se aplica? 1% chance = MUST invoke"
       │
       ▼
[Fase 0 — SEMPRE ATIVA (9 skills: 8 core + secrets-management)]
  concise-planning
  systematic-debugging
  lint-and-validate
  git-pushing
  kaizen
  verification-before-completion
  dispatching-parallel-agents
  enforcement-layer
  SECURITY/secrets-management
       │
       ▼
[Profession — SEMPRE ATIVA]
  news-curator (curadoria, editorial, PT-PT, pipeline)
       │
       ▼
[Classificar Request]
  Tipo: IDEA | PLAN | BUILD | FIX | TEST | DEPLOY | REFACTOR | REVIEW | ADAPT | SECURE
       │
       ▼
[Identificar Fase(s)]
  Match keywords → Fases 1-6
       │
       ▼
[Selecionar Skills]
  Dentro de cada fase, ativar por relevancia
       │
       ▼
[SECURITY GATE]                        ← para requests tipo DEPLOY
  Se o request e DEPLOY: verificar Security-by-Default Checklist
  (ver SECURITY/SECURITY.md)
       │
       ▼
[PRODUCTION READINESS GATE]            ← AUTO em DEPLOY
  SECURITY/production-readiness verifica: containers, CI/CD,
  monitoring, backups, process management, DB producao
       │
       ▼
[Executar com Skills Ativas]
  Aplicar conhecimento combinado
       │
       ▼
[VERIFICATION GATE]
  Antes de declarar "done": evidencia fresca obrigatoria
  lint-and-validate + testes se aplicavel
```

---

## NoticIA — Contexto Especifico

### Pipeline V2 (Optimizado)
```
raw_events → [Dispatcher V2: dedup + filtro + batch LLM + quality gate] → intake_queue
  → [Fact-Checker: web search + verificacao] → [Escritor: PT-PT] → articles
```

### 53 Agentes (Supabase)
Roles: collector, dispatcher, reporter, fact_checker, auditor (deprecated),
       writer, editor, publisher, columnist, engineer, ceo, hr

### Modelos Ativos
- gpt-oss:20b (dispatcher, publisher) — routing rapido
- mistral-large-3:675b (reporter, writer) — escrita PT-PT
- deepseek-v3.2 (fact_checker) — verificacao profunda
- cogito-2.1:671b (editor, ceo, hr) — julgamento editorial
- gemma3:27b (columnist) — escrita criativa
- devstral-2:123b (engineer) — codigo

### Infraestrutura
- Oracle Cloud ARM64 VM (82.70.84.122)
- systemd: noticia-pipeline, noticia-telegram, noticia-diretor-elite
- Supabase: ljozolszasxppianyaac
- Deploy: SSH + systemctl restart

---

## Extensoes

### Professions (`professions/`)
- `professions/news-curator/SKILL.md` — Curadoria de noticias AI (SEMPRE ATIVA)

### SECURITY (`SECURITY/`)
Framework de seguranca com 8 skills e documento mestre:
- `SECURITY/SECURITY.md` — Guia mestre, defense-in-depth, checklists
- `SECURITY/secrets-management/SKILL.md` — Fase 0, sempre ativa
- `SECURITY/threat-modeling/SKILL.md` — Fase 2
- `SECURITY/compliance-privacy/SKILL.md` — Fase 2
- `SECURITY/supply-chain-security/SKILL.md` — Fase 5
- `SECURITY/infrastructure-hardening/SKILL.md` — Fase 6
- `SECURITY/devsecops-pipeline/SKILL.md` — Fase 6
- `SECURITY/incident-response/SKILL.md` — Fase 6
- `SECURITY/production-readiness/SKILL.md` — Fase 6, AUTO em DEPLOY

### Workflows (`workflows/`)
Sequencias pre-definidas de skills:
- `workflows/brainstorm.md` — Ideacao completa
- `workflows/plan.md` — Planeamento tecnico
- `workflows/debug.md` — Debug sistematico
- `workflows/security-audit.md` — Auditoria de seguranca completa
- `workflows/harden.md` — Hardening de infraestrutura
- `workflows/incident.md` — Resposta a incidentes

---

*Atualizar este ficheiro sempre que adicionar/remover skills.*
