# Project Instructions — Curador de Noticias

## OBRIGATORIO: Ler antes de qualquer tarefa

**IMPORTANTE: Ler estes ficheiros no inicio de CADA conversa:**

1. `ARCHITECTURE-MASTER.md` — Fonte de verdade do sistema: todos os ~45 agentes, pipeline, schema DB, estado atual, plano de construcao
2. `SKILLS/claude.md` — Routing rules, phase classifier, and priority tiers
3. `SKILLS/ARCHITECTURE.md` — Complete map of all skills and routing matrix

**Ficheiros de referencia (ler quando relevante):**
- `AGENT-PROFILES.md` — Personalidades detalhadas dos agentes editoriais (Auditor, Escritor, Editor-Chefe, 10 Cronistas) com referencias intelectuais, estilo de escrita e instrucoes de system prompt
- `FACT-CHECKING.md` — Spec detalhada do modulo fact-check (6 checkers + Grok API)
- `FONTES.md` — Inventario completo de fontes de dados (RSS, GDELT, X, Telegram, etc.)
- `ROADMAP.md` — Plano de evolucao futura e API keys necessarias

---

## Sobre o Projeto

Sistema editorial autonomo ("redacao automatizada") que recolhe noticias de multiplas fontes globais, verifica factos com IA, escreve artigos em PT-PT, e publica com diferentes niveis de prioridade (P1 breaking, P2 importantes, P3 analise).

**Componentes principais (~45 agentes):**
- 7 Coletores (RSS, GDELT, X, Telegram, Event Registry, ACLED, Crawl4AI)
- 1 Dispatcher (routing de eventos para reporters)
- 20 Reporters Especialistas (fact-check forense + bias detection + filtro relevancia PT)
- 3 Agentes Editoriais (Auditor "O Cetico", Escritor PT-PT, Editor-Chefe)
- 3 Publishers (P1 cada 30min, P2 cada 3h, P3 2x/dia)
- 10 Cronistas com personalidade/ideologia (analises semanais)
- 4 Engenheiros (Frontend, Backend, UI, Chefe — monitorizacao + auto-correcao)

---

## Skills System

This project uses the SOTA Skills system for structured, phase-based development.

**How it works:**
- Phase 0 skills are ALWAYS active (planning, debugging, linting, git, kaizen)
- Other skills are activated automatically based on the request type and keywords
- See `SKILLS/claude.md` Section 3 (Router) for the full routing logic

**Skill files location:** Each skill lives in `SKILLS/<skill-name>/SKILL.md`

---

## Tech Stack

- **Frontend:** Next.js 15 + TypeScript + Tailwind CSS
- **Runtime:** Node.js
- **Database:** Supabase (PostgreSQL) — projeto `ljozolszasxppianyaac`
- **Edge Functions:** Supabase Edge Functions (Deno/TypeScript)
- **Pipeline Local:** Python 3 + APScheduler (em `pipeline/`)
- **LLM:** Grok API (xAI) — modelo `grok-4-1-fast-reasoning`
- **Deploy:** Vercel (frontend) + Supabase (backend)

---

## Code Style

- Use strict TypeScript (`strict: true`) para frontend e Edge Functions
- Python com type hints para pipeline local
- Follow ESLint rules defined in project config
- Use conventional commits (see `SKILLS/commit/SKILL.md`)
- Linguagem dos artigos: **PT-PT** (facto, equipa, telemóvel — nunca PT-BR)

---

## File Structure

```
/ (raiz do projeto)
├── ARCHITECTURE-MASTER.md    → FONTE DE VERDADE do sistema
├── CLAUDE.md                 → Este ficheiro
├── FACT-CHECKING.md          → Spec do fact-check
├── FONTES.md                 → Inventario de fontes
├── ROADMAP.md                → Plano futuro
├── src/                      → Frontend Next.js
│   ├── app/                  → Routes e pages
│   ├── components/           → UI components
│   ├── lib/                  → Supabase client, utilities
│   └── types/                → TypeScript types
├── pipeline/                 → Pipeline Python (agentes locais)
│   └── src/openclaw/
│       ├── collectors/       → 7 coletores
│       ├── reporters/        → 14 reporters (fact-check forense + bias detection)
│       ├── curador/          → Dedup + filas de prioridade
│       ├── editorial/        → Editor-Chefe + Grok client
│       ├── factcheck/        → 7 modulos de verificacao
│       ├── output/           → Publisher para Supabase
│       └── scheduler/        → APScheduler runner
├── supabase/
│   └── functions/            → 20 Edge Functions deployed
├── SKILLS/                   → SOTA Skills system (37 skills)
└── archive/                  → Docs historicos (nao usar como referencia)
```

---

## Git Workflow

- Branch from `main`
- Branch naming: `type/short-description` (e.g., `feat/user-auth`)
- PR required for merge to `main`
- All tests must pass before merge

---

## REGRAS IMPORTANTES

1. **NUNCA usar ficheiros de `/archive/`** como referencia — estao obsoletos
2. **Sempre consultar `ARCHITECTURE-MASTER.md`** para entender o estado atual do sistema
3. **Artigos em PT-PT** — nunca PT-BR (ex: "facto" nao "fato", "equipa" nao "time")
4. **Supabase project ID:** `ljozolszasxppianyaac`
5. **Grok API:** usar `/v1/responses` para fact-check (com tools), `/v1/chat/completions` para writer
