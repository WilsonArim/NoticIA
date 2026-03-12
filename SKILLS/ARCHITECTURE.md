# ARCHITECTURE — Mapa de Skills, Fases & Routing

> Referencia completa de todas as skills, organizacao por fases, e matriz de routing.

---

## Visao Geral

```
Total de Skills: 33
Fases: 7 (0-6)
Skills Fase 0 (sempre ativas): 5
Skills sob demanda: 28
Professions: extensivel (user-managed)
Workflows: 3
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

### FASE 3 — Backend

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Backend Dev Guidelines | `backend-dev-guidelines/` | Padroes Node.js/Express/TypeScript |
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

### FASE 6 — Deploy & Manutencao

| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| Docker Expert | `docker-expert/` | Containers e multi-stage builds |
| Deployment Procedures | `deployment-procedures/` | Rollout seguro, CI/CD |
| Commit | `commit/` | Conventional commits |
| Create PR | `create-pr/` | PRs com contexto para review |
| Changelog Automation | `changelog-automation/` | Release notes consistentes |

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

BACKEND:
  backend|servidor|Node|Express       → backend-dev-guidelines, senior-fullstack
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

DEPLOY:
  Docker|container|imagem             → docker-expert
  deploy|producao|rollout|CI/CD       → deployment-procedures
  commit|mensagem                     → commit
  PR|pull-request|merge               → create-pr
  changelog|release|versao            → changelog-automation
```

### Complexidade → Combinacao de Skills

| Complexidade | Comportamento |
|-------------|---------------|
| Simples (1 ficheiro, 1 tarefa) | 1-2 skills da fase relevante |
| Media (multiplos ficheiros, 1 feature) | 2-4 skills, possivelmente cross-fase |
| Alta (sistema completo, multiplas features) | 4+ skills, multiplas fases em sequencia |

---

## Fluxo de Ativacao

```
[Pedido do Utilizador]
       │
       ▼
[Fase 0 — SEMPRE ATIVA]
  concise-planning
  systematic-debugging
  lint-and-validate
  git-pushing
  kaizen
       │
       ▼
[Classificar Request]
  Tipo: IDEA | PLAN | BUILD | FIX | TEST | DEPLOY | REFACTOR | REVIEW | ADAPT
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
[Executar com Skills Ativas]
  Aplicar conhecimento combinado
       │
       ▼
[Validar]
  lint-and-validate + testes se aplicavel
```

---

## Extensoes

### Professions (`professions/`)
Skills de profissao com formato identico. Exemplos:
- `professions/journalist/SKILL.md`
- `professions/lawyer/SKILL.md`
- `professions/data-scientist/SKILL.md`

### Workflows (`workflows/`)
Sequencias pre-definidas de skills:
- `workflows/brainstorm.md` — Ideacao completa
- `workflows/plan.md` — Planeamento tecnico
- `workflows/debug.md` — Debug sistematico

---

*Atualizar este ficheiro sempre que adicionar/remover skills.*
