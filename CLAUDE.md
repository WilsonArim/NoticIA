# Project Instructions

## Skills System

This project uses the SOTA Skills system for structured, phase-based development.

**IMPORTANT: Read these files at the start of every conversation:**

1. `SKILLS/claude.md` — Routing rules, phase classifier, and priority tiers
2. `SKILLS/ARCHITECTURE.md` — Complete map of all skills and routing matrix

**How it works:**

- Phase 0 skills are ALWAYS active (planning, debugging, linting, git, kaizen)
- Other skills are activated automatically based on the request type and keywords
- See `SKILLS/claude.md` Section 3 (Router) for the full routing logic

**Skill files location:** Each skill lives in `SKILLS/<skill-name>/SKILL.md`

---

## Project Conventions

<!-- Customize these for each project -->

### Tech Stack
- Language: TypeScript
- Runtime: Node.js
- Framework: (define here)
- Database: (define here)
- Styling: (define here)

### Code Style
- Use strict TypeScript (`strict: true`)
- Follow ESLint rules defined in project config
- Use conventional commits (see `SKILLS/commit/SKILL.md`)

### File Structure
```
src/
├── app/          → Routes and pages
├── components/   → Reusable UI components
├── lib/          → Shared utilities and helpers
├── server/       → Server-side logic
└── types/        → Shared TypeScript types
```

### Git Workflow
- Branch from `main`
- Branch naming: `type/short-description` (e.g., `feat/user-auth`)
- PR required for merge to `main`
- All tests must pass before merge
