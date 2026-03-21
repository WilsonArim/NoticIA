# NoticIA — Project Instructions

## Skills System

This project uses the SOTA Skills system for structured, phase-based development.

**IMPORTANT: Read these files at the start of every conversation:**

1. `SKILLS/claude.md` — Routing rules, phase classifier, and priority tiers
2. `SKILLS/ARCHITECTURE.md` — Complete map of all skills and routing matrix
3. `SKILLS/SECURITY/SECURITY.md` — Security posture, defense-in-depth layers, and security skills

**How it works:**

- Phase 0 skills are ALWAYS active (planning, debugging, linting, git, kaizen, secrets-management)
- Security skills are activated automatically when infrastructure, deploy, or security keywords are detected
- `secrets-management` is ALWAYS active (Phase 0) — secrets discipline applies to every task
- Other skills are activated automatically based on the request type and keywords
- See `SKILLS/claude.md` Section 3 (Router) for the full routing logic
- **Profession skill `professions/news-curator/SKILL.md`** is ALWAYS active — this is a news curation project

**Skill files location:** Each skill lives in `SKILLS/<skill-name>/SKILL.md`
**Security skills location:** `SKILLS/SECURITY/<skill-name>/SKILL.md`

---

## Security Posture

This project follows a **defense-in-depth** security model with 8 layers.
See `SKILLS/SECURITY/SECURITY.md` for the complete security framework.

**Always-active security rules:**
- Never commit secrets, API keys, tokens, or credentials to version control
- All secrets live in `.env` (which is in `.gitignore`) — use `.env.example` for documentation
- Pre-commit hooks must include secret detection (gitleaks or truffleHog)
- Every deploy must pass the Security-by-Default Checklist (see SECURITY.md)

**Security skills (8):**
- `SECURITY/secrets-management` — Phase 0, ALWAYS active
- `SECURITY/threat-modeling` — Phase 2 (Architecture)
- `SECURITY/compliance-privacy` — Phase 2 (Architecture)
- `SECURITY/supply-chain-security` — Phase 5 (Quality)
- `SECURITY/infrastructure-hardening` — Phase 6 (Deploy)
- `SECURITY/devsecops-pipeline` — Phase 6 (Deploy)
- `SECURITY/incident-response` — Phase 6 (Deploy)
- `SECURITY/production-readiness` — Phase 6 (Deploy, AUTO on every DEPLOY request)

---

## Project Overview

**NoticIA** is an AI-powered Portuguese news curation pipeline that collects, classifies, fact-checks, and publishes news articles in PT-PT (European Portuguese). The system runs on an Oracle Cloud VM with 53 autonomous agents orchestrated through a multi-stage pipeline.

### Mission
Curate high-quality, fact-checked Portuguese news with minimal human intervention, maintaining journalistic standards and editorial quality through AI agents.

---

## Tech Stack

### Backend Pipeline (Python)
- **Language:** Python 3.12
- **Runtime:** CPython on Ubuntu 22.04 (Oracle Cloud ARM64)
- **LLM Provider:** Ollama Pro API (OpenAI-compatible) — `https://ollama.com`
- **Database:** Supabase (PostgreSQL + RLS + Edge Functions)
- **Scheduler:** APScheduler (BackgroundScheduler)
- **Web Search:** Tavily → Exa.ai → Serper.dev (fallback chain)
- **Telegram:** Telethon (bot mode) + OpenAI client
- **Package Manager:** pip + venv

### Frontend (Next.js)
- **Framework:** Next.js 15+ with TypeScript
- **Styling:** Tailwind CSS + PostCSS
- **Deployment:** Vercel
- **Supabase Client:** @supabase/supabase-js

### Infrastructure
- **VM:** Oracle Cloud ARM64 (ubuntu@82.70.84.122)
- **SSH Key:** `~/.ssh/oracle_noticia.key`
- **Process Manager:** systemd (3 services)
- **Supabase Project:** `ljozolszasxppianyaac`
- **SSH:** Ed25519 key-only auth (password auth disabled)
- **Protection:** Fail2Ban (SSH jail, 3 retries, 1h ban)
- **Reverse Proxy:** Nginx with rate limiting + security headers
- **Monitoring:** healthcheck.sh (5min), backup.sh (daily 3h), db_cleanup.sh (weekly)
- **Swap:** 4GB swapfile (vm.swappiness=10)

---

## Models & Roles

The `.env` is the **single source of truth** for model assignments. On startup, `sync_models_to_supabase()` propagates models to the `adapter_config.model` field in Supabase.

| Role | Env Variable | Model | Purpose |
|------|-------------|-------|---------|
| dispatcher | `MODEL_DISPATCHER` | gpt-oss:20b | Fast routing, classification, batch scoring |
| reporter | `MODEL_REPORTER` | mistral-large-3:675b | News reporting in PT-PT |
| fact_checker | `MODEL_FACTCHECKER` | deepseek-v3.2 | Deep factual verification + web search |
| auditor | `MODEL_AUDITOR` | cogito-2.1:671b | DEPRECATED — collapsed into dispatcher V2 quality gate |
| writer | `MODEL_ESCRITOR` | mistral-large-3:675b | Article writing in PT-PT |
| editor | `MODEL_EDITOR_CHEFE` | cogito-2.1:671b | Editorial judgment, final review |
| columnist | `MODEL_CRONISTAS` | gemma3:27b | Creative/expressive writing |
| ceo | `MODEL_EDITOR_CHEFE` | cogito-2.1:671b | Strategic decisions |
| engineer | `MODEL_ENGINEER` | devstral-2:123b | Code generation/debugging |
| publisher | `MODEL_DISPATCHER` | gpt-oss:20b | Lightweight publish actions |
| collector | — | (no LLM) | Data collection only |

### Specialty Models (auxiliary)
| Env Variable | Model | Purpose |
|-------------|-------|---------|
| `MODEL_VISION` | nvidia/nemotron-nano-12b-v2-vl:free | Image analysis |
| `MODEL_SAFETY` | nvidia/nemotron-content-safety-reasoning-4b | Content safety |
| `MODEL_TRANSLATE` | nvidia/riva-translate-4b-instruct-v1_1 | Translation |
| `MODEL_DOSSIE` | kimi-k2-thinking | Deep research/dossiers |

---

## Pipeline Architecture (V2)

```
raw_events (collectors: RSS, GDELT, ACLED, EventRegistry, Crawl4AI, Telegram)
    │
    ▼
[Dispatcher V2]  every 5 min
  ├── Dedup (title_hash MD5) ────────────── ~7% eliminated pre-LLM
  ├── Deterministic filter ──────────────── ~60-70% eliminated pre-LLM
  │   (domain blocklist, keyword blocklist, content length, staleness)
  ├── Batch LLM classification ──────────── 10 events per call (~78% fewer tokens)
  └── Quality gate (score 0-10, threshold 5.0) ── replaces auditor stage
    │
    ▼
intake_queue (status='auditor_approved')
    │
    ▼
[Fact-Checker]  every 25 min
  └── Web search (Tavily→Exa→Serper) + factual verification
    │
    ▼
intake_queue (status='approved')
    │
    ▼
[Escritor]  every 30 min
  └── Article writing in PT-PT + atomic publication
    │
    ▼
articles (status='published')
```

### Systemd Services
- `noticia-pipeline.service` — Main scheduler (dispatcher + fact-checker + escritor)
- `noticia-telegram.service` — Telegram collector
- `noticia-diretor-elite.service` — Diretor Elite Telegram bot (interactive)

---

## File Structure

```
~/noticia/
├── CLAUDE.md                          → This file (project instructions)
├── SKILLS/                            → SOTA Skills system (45 skills + 1 profession)
│   ├── claude.md                      → Router configuration
│   ├── ARCHITECTURE.md                → Skills map & routing matrix
│   ├── SECURITY/                      → Security framework (8 skills)
│   │   ├── SECURITY.md               → Master security document
│   │   ├── secrets-management/        → Phase 0, ALWAYS active
│   │   ├── threat-modeling/           → Phase 2
│   │   ├── compliance-privacy/        → Phase 2
│   │   ├── supply-chain-security/     → Phase 5
│   │   ├── infrastructure-hardening/  → Phase 6
│   │   ├── devsecops-pipeline/        → Phase 6
│   │   ├── incident-response/         → Phase 6
│   │   └── production-readiness/      → Phase 6, AUTO on DEPLOY
│   └── <skill-name>/SKILL.md          → Individual skill files
│
├── pipeline/                          → Python backend pipeline
│   ├── .env                           → Single source of truth (models, keys)
│   ├── venv/                          → Python virtual environment
│   └── src/openclaw/
│       ├── agents/
│       │   ├── dispatcher.py          → V2: dedup + filter + batch LLM + quality gate
│       │   ├── fact_checker.py        → Web search + factual verification
│       │   ├── escritor.py            → PT-PT article writer
│       │   ├── ollama_client.py       → OpenAI-compatible Ollama Pro client
│       │   ├── triagem.py             → DEPRECATED (replaced by dispatcher LLM)
│       │   └── injetor.py             → Manual CLI injection tool
│       ├── collectors/
│       │   ├── base.py                → BaseCollector (abstract)
│       │   ├── rss.py                 → RSS feed collector
│       │   ├── gdelt.py               → GDELT news collector
│       │   ├── acled.py               → ACLED conflict data
│       │   ├── event_registry.py      → EventRegistry API
│       │   ├── crawl4ai_collector.py  → Web crawler collector
│       │   └── telegram_collector.py  → Telegram channel collector
│       ├── output/
│       │   └── supabase_intake.py     → Supabase intake queue writer
│       ├── scheduler/
│       │   └── runner.py              → Scheduler runner
│       ├── models.py                  → RawEvent dataclass (event_hash = sha256(url:source))
│       ├── config.py                  → Configuration
│       ├── scheduler_ollama.py        → V2 scheduler (APScheduler)
│       └── tests/                     → Test suite
│
├── telegram-bot/                      → Diretor Elite Telegram bot
│   ├── bot.py                         → Telethon bot + OpenAI/Ollama client
│   ├── .env                           → Bot-specific config
│   └── .venv/                         → Bot virtual environment
│
├── telegram-collector/                → Telegram source collector
│
├── scripts/                           → Operational scripts
│   ├── healthcheck.sh                 → Service health monitoring (every 5 min)
│   ├── backup.sh                      → Daily backup at 3am (30-day retention)
│   └── db_cleanup.sh                  → Weekly DB cleanup (Sundays 4am)
│
├── .github/workflows/ci.yml          → CI pipeline (lint + validate)
│
├── src/                               → Next.js frontend
│   ├── lib/supabase/                  → Supabase client, types, middleware
│   ├── lib/utils/                     → Utility functions
│   ├── lib/constants/                 → Categories, etc.
│   └── components/                    → React components (ArticleCard, etc.)
│
├── supabase/
│   ├── functions/                     → Edge Functions
│   └── migrations/                    → SQL migrations
│
├── public/                            → Static assets
├── docs/                              → Documentation
├── PROMPTS/                           → Agent prompt templates
└── archive/                           → Archived code/configs
```

---

## Database Schema (Supabase)

### Core Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `raw_events` | Incoming events from collectors | `id`, `title`, `url`, `content`, `source_collector`, `processed`, `published_at`, `event_hash`, `title_hash` |
| `intake_queue` | Events pending editorial pipeline | `id`, `title`, `content`, `categories`, `priority`, `relevance_score`, `status`, `title_hash` |
| `articles` | Published articles | `id`, `title`, `body`, `sources`, `status`, `fact_check_score` |
| `agents` | 53 agent definitions | `id`, `name`, `role`, `adapter_config`, `status` |
| `pipeline_runs` | Pipeline execution logs | `id`, `agent_id`, `started_at`, `finished_at`, `status`, `metadata` |

### Dedup Strategy
- `event_hash` = `sha256(url + ":" + source_collector)` — dedup by URL in raw_events
- `title_hash` = `md5(lower(trim(regexp_replace(title, '\s+', ' ', 'g'))))` — dedup by normalized title across raw_events and intake_queue

### Key Indexes
```sql
idx_raw_events_title_hash ON raw_events(title_hash)
idx_raw_events_unprocessed_recent ON raw_events(processed, published_at DESC) WHERE processed = false
idx_intake_queue_title_hash ON intake_queue(title_hash)
```

---

## Code Style & Conventions

### Python (Pipeline)
- Python 3.12+ with type hints everywhere
- Docstrings: Google style (module, class, function)
- Logging: `logging` module with `%(asctime)s %(name)s %(levelname)s %(message)s`
- Error handling: Never crash the scheduler — catch exceptions per-job, log, retry next cycle
- Environment: All secrets and config in `.env`, loaded via `python-dotenv`
- Imports: stdlib → third-party → local (separated by blank lines)
- No hardcoded URLs, keys, or model names — always from `.env`

### TypeScript (Frontend)
- Strict TypeScript (`strict: true`)
- Follow ESLint config in project root
- React server components by default (Next.js 15+)
- Tailwind CSS for styling

### Language Rules (PT-PT)
- All article output MUST be in European Portuguese (PT-PT), never Brazilian Portuguese
- Use: "facto" not "fato", "equipa" not "time", "telemóvel" not "celular"
- Formal register for news articles
- Agent names and logs can be in Portuguese or English (consistency within each file)

---

## Git Workflow

- Branch from `main`
- Branch naming: `type/short-description` (e.g., `feat/dispatcher-v2`, `fix/dedup-bug`)
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `perf:`, `test:`
- PR required for merge to `main`
- All tests must pass before merge
- **CRITICAL:** Never commit `.env` files or API keys
- Signed commits recommended (see `SKILLS/SECURITY/supply-chain-security/SKILL.md`)

---

## SSH & Deployment

### Connecting to VM
```bash
ssh -i ~/.ssh/oracle_noticia.key ubuntu@82.70.84.122
```

### Managing Services
```bash
sudo systemctl status noticia-pipeline
sudo systemctl restart noticia-pipeline
sudo journalctl -u noticia-pipeline -f --no-pager -n 50
```

### Pipeline Activation
```bash
cd ~/noticia/pipeline && source venv/bin/activate
python -m openclaw.scheduler_ollama
```

### Deploying Changes
1. SSH into VM
2. `cd ~/noticia && git pull` (or scp files directly)
3. For pipeline: `sudo systemctl restart noticia-pipeline`
4. For telegram-bot: `sudo systemctl restart noticia-diretor-elite`
5. Verify logs: `sudo journalctl -u <service> -f`

---

## Key Design Decisions

1. **Batch LLM over individual calls** — 10 events per LLM call reduces tokens by ~78%
2. **Deterministic pre-filtering** — Domain/keyword blocklists eliminate ~60-70% without LLM
3. **Title hash dedup** — MD5 of normalized title catches near-duplicates across sources
4. **Quality gate in dispatcher** — Score 0-10 replaces separate auditor stage
5. **Events retry on LLM failure** — Only mark `processed=True` after successful LLM classification
6. **Fallback web search chain** — Tavily → Exa.ai → Serper.dev ensures fact-checking always has a search provider
7. **`.env` as single source of truth** — `sync_models_to_supabase()` propagates to agents table on startup
8. **Atomic article publication** — `publish_article_with_sources` RPC ensures consistency

---

## Known Issues & Technical Debt

- [ ] No automated tests (test suite exists but is empty)
- [ ] CI pipeline validates but does not auto-deploy (manual deploy via SSH)
- [ ] `triagem.py` is deprecated but still in codebase
- [ ] Frontend and pipeline share the same repo (monorepo without proper tooling)
- [ ] Services run in venvs, not Docker containers (production-readiness skill recommends containerization)
- [ ] No structured logging (plain text logs)
- [ ] No centralized log shipping

### Resolved (March 2026 Audit)
- [x] ~~No monitoring/alerting~~ → healthcheck.sh (5min) + Telegram alerts
- [x] ~~No backup strategy~~ → backup.sh (daily 3am, 30-day retention)
- [x] ~~No swap configured~~ → 4GB swapfile, vm.swappiness=10
- [x] ~~Fail2Ban inactive~~ → SSH jail active (3 retries, 1h ban)
- [x] ~~PAT exposed in git remote~~ → SSH key auth (Ed25519), PAT revoked
- [x] ~~No CI/CD pipeline~~ → GitHub Actions CI (lint + validate)
- [x] ~~No rate limiting~~ → Nginx rate limiting + security headers
- [x] ~~SSH password auth enabled~~ → Key-only, PermitRootLogin no, MaxAuthTries 3
- [x] ~~No DB cleanup~~ → db_cleanup.sh (weekly, Supabase REST API)
- [x] ~~.gitignore incomplete~~ → Updated with NoticIA-specific exclusions

---

*This file is read automatically by Claude. Update it when the project architecture changes.*
