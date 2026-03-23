# NoticIA V3 — Contra-Media AI Platform (Project Instructions)

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

**NoticIA V3** is an AI-powered Portuguese contra-media platform. It is NOT a generic news channel — it is a counter-media system that:

1. **Audits mainstream media** — Detects bias, framing manipulation, and factual omissions
2. **Covers ignored news** — Publishes stories that mainstream media won't cover (alt-news)
3. **Accepts editorial injections** — Wilson (CEO) injects URLs via Telegram for the pipeline to process
4. **Detects omissions automatically** — Coverage Analyzer cross-references sources every 6 hours

### Mission V3
Expose mainstream media bias, cover suppressed stories, and give Portuguese readers the other side of every story — all in PT-PT with AI-powered fact-checking and editorial judgment.

### Three Vertentes (Content Streams)
| Vertente | Source | FC Mode | Purpose |
|----------|--------|---------|---------|
| `media_watch` | RSS/GDELT (mainstream) | Audit honesty, framing, omissions | Find and expose bias |
| `alt_news` | Telegram (alternative) | Rigorous verification (3+ sources) | Verify alternative narratives |
| `editorial` | Wilson via `/injecta` | Fact-check manual injections | Process CEO's editorial picks |

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
- **SSH Key:** `~/.ssh/oracle_noticia.key` (Ed25519)
- **Process Manager:** Docker Compose (3 containers) + auto-restart
- **Supabase Project:** `ljozolszasxppianyaac`
- **SSH:** Ed25519 key-only auth (password auth disabled)
- **Protection:** Fail2Ban (SSH jail, 3 retries, 1h ban)
- **Reverse Proxy:** Nginx with rate limiting + security headers
- **Monitoring:** engenheiro_pipeline.py (30min), healthcheck.sh (5min), backup.sh (daily 3h), db_cleanup.sh (weekly)
- **Swap:** 4GB swapfile (vm.swappiness=10)

---

## Models & Roles

The `.env` is the **single source of truth** for model assignments. On startup, `sync_models_to_supabase()` propagates models to the `adapter_config.model` field in Supabase.

**IMPORTANT: No Chinese models (DeepSeek, Qwen, Cogito) are allowed in fact-checking — they carry Chinese censorship bias.**

| Role | Env Variable | Model | Purpose |
|------|-------------|-------|---------|
| dispatcher | `MODEL_DISPATCHER` | gpt-oss:20b | Fast routing, classification, batch scoring, vertente mapping |
| reporter | `MODEL_REPORTER` | mistral-large-3:675b | News reporting in PT-PT |
| fact_checker | `MODEL_FACTCHECKER` | mistral-large-3:675b | Dual-mode FC: media audit / alt verification / editorial check |
| writer | `MODEL_ESCRITOR` | mistral-large-3:675b | Article writing in PT-PT (6 templates) |
| editor | `MODEL_EDITOR_CHEFE` | mistral-large-3:675b | Editorial judgment, final review |
| columnist | `MODEL_CRONISTAS` | gemma3:27b | Creative/expressive writing (10 weekly chronicles) |
| ceo | `MODEL_EDITOR_CHEFE` | mistral-large-3:675b | Strategic decisions |
| engineer | `MODEL_ENGINEER` | devstral-2:123b | Code generation/debugging |
| publisher | `MODEL_DISPATCHER` | gpt-oss:20b | Lightweight publish actions |
| collector | — | (no LLM) | Data collection only |

### Specialty Models (auxiliary)
| Env Variable | Model | Purpose |
|-------------|-------|---------|
| `MODEL_VISION` | nvidia/nemotron-nano-12b-v2-vl:free | Image analysis |
| `MODEL_SAFETY` | nvidia/nemotron-content-safety-reasoning-4b | Content safety |
| `MODEL_TRANSLATE` | nvidia/riva-translate-4b-instruct-v1_1 | Translation |
| `MODEL_DOSSIE` | kimi-k2-thinking | Deep research/dossiers (único modelo chinês restante — investigação profunda, não fact-checking) |

---

## Pipeline Architecture V3 (Contra-Media)

```
raw_events (collectors: RSS, GDELT, Telegram, Editorial Injection)
  │  source_type: media | alternative | editorial_injection
  │
  ▼
[Dispatcher V3]  every 5 min
  ├── Dedup (title_hash MD5) ────────────── ~7% eliminated pre-LLM
  ├── Deterministic filter ──────────────── ~60-70% eliminated pre-LLM
  │   (domain blocklist, keyword blocklist, content length, staleness)
  ├── Batch LLM classification ──────────── 10 events per call (~78% fewer tokens)
  ├── Quality gate (score 0-10, threshold 5.0)
  └── Vertente routing ─────────────────── source_type → vertente
      media → media_watch | alternative → alt_news | editorial_injection → editorial
  │
  ▼
intake_queue (status='auditor_approved', vertente set)
  │
  ▼
[Fact-Checker V3 Dual-Mode]  every 25 min (6 parallel sectors)
  ├── media_watch: Audita honestidade, framing, omissões (busca o OUTRO LADO)
  │   → bias_verdict: {bias_type, severity, omitted_facts, counter_narrative}
  │   → media_audit: {publish_recommendation: expose|omission|discard|needs_review}
  ├── alt_news: Verificação rigorosa (exige 3+ fontes independentes)
  │   → bias_verdict: {verified: true/false, sources_found, confidence}
  └── editorial: Verifica factos de injecções manuais do Wilson
      → bias_verdict: {factual_accuracy, corrections_needed}
  │
  ▼
intake_queue (status='approved', bias_verdict + media_audit filled)
  │
  ▼
[Decisor Editorial V3]  every 10 min (DETERMINISTIC GATE)
  ├── media_watch + NO bias detected ────── → DISCARD (não nos interessa)
  ├── media_watch + bias severity > 0.20 ── → EXPOSÉ
  ├── media_watch + omitted_facts ≥ 2 ───── → OMISSION article
  ├── media_watch + ambiguous ────────────── → WILSON_REVIEW (via Telegram)
  ├── alt_news + verified ────────────────── → ALT_NEWS article
  └── editorial ──────────────────────────── → EDITORIAL / FACT_CHECK article
  │
  ▼
intake_queue (status='ready_to_write' | 'discarded' | 'wilson_review')
  │
  ▼
[Escritor V3]  every 30 min (6 TEMPLATES)
  ├── template_expose()    — "Os media disseram X, mas a realidade é Y"
  ├── template_omission()  — "O que os media NÃO contaram sobre X"
  ├── template_alt_news()  — Verified alternative news article
  ├── template_fact_check() — Fact-check with verdict
  ├── template_editorial() — Wilson's editorial pick
  └── template_standard()  — Fallback standard article
  │
  ▼
articles (status='published', article_type set)
```

### Additional V3 Jobs
| Job | Interval | Purpose |
|-----|----------|---------|
| Coverage Analyzer | 6 hours | Cross-references alternative vs mainstream sources, detects stories only alt-sources cover → inserts omission candidates into intake_queue |
| Pipeline Health (Engenheiro) | 30 min | Monitors all 7 pipeline stages, V3 statuses, bias_verdict fields, discard rates, Telegram alerts |
| Cronistas | Sunday 10:00 UTC | Generates 10 weekly chronicles |

### Status Flow V3
```
raw_events → [Dispatcher] → auditor_approved
  → [Fact-Checker] → approved (with bias_verdict + media_audit)
  → [Decisor Editorial] → ready_to_write | discarded | wilson_review
  → [Escritor] → published (articles table, with article_type)
```

### Docker Containers (3)
| Container | Service | Health Check |
|-----------|---------|-------------|
| `noticia-pipeline` | Scheduler V3 (8 jobs) | Process alive |
| `noticia-diretor-elite` | Telegram bot (Diretor Elite) | Bot responsive |
| `noticia-telegram-collector` | Telegram channel collector | Process alive |

**CRITICAL:** `docker compose restart` does NOT rebuild images. Code changes require:
```bash
docker compose build pipeline telegram-bot && docker compose up -d
```

---

## Telegram Bot (Diretor Elite V3)

### Commands
| Command | Purpose |
|---------|---------|
| `/investiga [tema]` | Launch deep investigation (dossier) |
| `/injecta URL [contexto]` | Inject URL into pipeline as editorial_injection |
| `/status` | Pipeline status report |
| `/relatorio` | Detailed performance report |
| `/arquivo` | Search article archive |

### /injecta Flow
1. Wilson sends `/injecta https://example.com optional context`
2. Bot fetches URL content (title + body via httpx)
3. Inserts into `raw_events` with `source_type='editorial_injection'`, `source_collector='editorial_injection'`
4. Pipeline processes through full V3 flow (FC → Decisor → Escritor) with vertente='editorial'

---

## File Structure

```
~/noticia/
├── CLAUDE.md                          → This file (project instructions V3)
├── DIARIO-DE-BORDO.md                 → Pipeline diary (auto-updated by engenheiro)
├── PLANO-V3-CONTRA-MEDIA.md           → V3 implementation plan
├── SKILLS/                            → SOTA Skills system (45 skills + 1 profession)
│   ├── claude.md                      → Router configuration
│   ├── ARCHITECTURE.md                → Skills map & routing matrix
│   └── SECURITY/                      → Security framework (8 skills)
│
├── pipeline/                          → Python backend pipeline
│   ├── .env                           → Single source of truth (models, keys)
│   ├── Dockerfile                     → Pipeline container image
│   ├── venv/                          → Python virtual environment
│   └── src/openclaw/
│       ├── agents/
│       │   ├── dispatcher.py          → V3: dedup + filter + batch LLM + vertente routing
│       │   ├── fact_checker.py        → V3: dual-mode FC (media_audit / alt_news / editorial)
│       │   ├── fact_checker_parallel.py → Parallel FC across 6 sectors
│       │   ├── editorial_decisor.py   → V3 NEW: deterministic gate (expose/omission/discard/wilson_review)
│       │   ├── escritor.py            → V3: 6 template writer (expose, omission, alt_news, fact_check, editorial, standard)
│       │   ├── coverage_analyzer.py   → V3 NEW: omission detector (every 6h)
│       │   ├── ollama_client.py       → OpenAI-compatible Ollama Pro client
│       │   └── injetor.py             → Manual CLI injection tool
│       ├── collectors/
│       │   ├── base.py                → BaseCollector (abstract)
│       │   ├── rss.py                 → RSS feed collector
│       │   ├── gdelt.py               → GDELT news collector
│       │   ├── acled.py               → ACLED conflict data
│       │   ├── event_registry.py      → EventRegistry API
│       │   ├── crawl4ai_collector.py  → Web crawler collector
│       │   └── telegram_collector.py  → Telegram channel collector (source_type='alternative')
│       ├── collector_runner.py        → V3: marks source_type per collector
│       ├── output/
│       │   └── supabase_intake.py     → Supabase intake queue writer
│       ├── scheduler/
│       │   └── runner.py              → Scheduler runner
│       ├── models.py                  → RawEvent dataclass (event_hash = sha256(url:source))
│       ├── config.py                  → Configuration
│       ├── scheduler_ollama.py        → V3 scheduler (8 jobs via APScheduler)
│       ├── engenheiro_pipeline.py     → V3 pipeline health monitor (7 probes + V3 diagnostics)
│       └── tests/                     → Test suite
│
├── telegram-bot/                      → Diretor Elite Telegram bot V3
│   ├── bot.py                         → V3: Telethon bot + /injecta command
│   ├── .env                           → Bot-specific config
│   └── .venv/                         → Bot virtual environment
│
├── telegram-collector/                → Telegram source collector
│
├── docker-compose.yml                 → 3 containers (pipeline, bot, collector)
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
│   └── migrations/                    → SQL migrations (incl. V3 foundation + RPC)
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
| `raw_events` | Incoming events from collectors | `id`, `title`, `url`, `content`, `source_collector`, `source_type` (V3), `processed`, `published_at`, `event_hash`, `title_hash` |
| `intake_queue` | Events in editorial pipeline | `id`, `title`, `content`, `categories`, `priority`, `relevance_score`, `status`, `title_hash`, `vertente` (V3), `bias_verdict` (V3 JSONB), `media_audit` (V3 JSONB) |
| `articles` | Published articles | `id`, `title`, `body`, `sources`, `status`, `fact_check_score`, `article_type` (V3) |
| `agents` | Agent definitions | `id`, `name`, `role`, `adapter_config`, `status` |
| `pipeline_runs` | Pipeline execution logs | `id`, `stage`, `started_at`, `completed_at`, `status`, `events_in`, `events_out`, `metadata` |

### V3 Columns (added in migration `v3_contra_media_foundation`)
| Table | Column | Type | Default | Purpose |
|-------|--------|------|---------|---------|
| `raw_events` | `source_type` | text | `'media'` | `media` / `alternative` / `editorial_injection` |
| `intake_queue` | `vertente` | text | `'media_watch'` | `media_watch` / `alt_news` / `editorial` |
| `intake_queue` | `bias_verdict` | jsonb | `'{}'` | FC output: bias_type, severity, omitted_facts, counter_narrative |
| `intake_queue` | `media_audit` | jsonb | `'{}'` | FC output: publish_recommendation, factos_correctos |
| `articles` | `article_type` | text | `'standard'` | `expose` / `omission` / `alt_news` / `fact_check` / `editorial` / `chronicle` / `standard` |

### V3 Status Values (intake_queue)
| Status | Set By | Meaning |
|--------|--------|---------|
| `auditor_approved` | Dispatcher | Passed quality gate, awaiting FC |
| `auditor_failed` | Dispatcher | Below quality threshold |
| `approved` | Fact-Checker | FC complete, awaiting Decisor |
| `fact_check` | Fact-Checker | Failed fact verification |
| `ready_to_write` | Decisor | Approved for article writing |
| `discarded` | Decisor | Media without bias — not interesting |
| `wilson_review` | Decisor | Ambiguous — needs Wilson's manual review |

### Dedup Strategy
- `event_hash` = `sha256(url + ":" + source_collector)` — dedup by URL in raw_events
- `title_hash` = `md5(lower(trim(regexp_replace(title, '\s+', ' ', 'g'))))` — dedup by normalized title across raw_events and intake_queue

### Key Indexes
```sql
idx_raw_events_title_hash ON raw_events(title_hash)
idx_raw_events_unprocessed_recent ON raw_events(processed, published_at DESC) WHERE processed = false
idx_intake_queue_title_hash ON intake_queue(title_hash)
```

### RPC Function
- `publish_article_with_sources(...)` — Atomic article publication. V3 version accepts `article_type` parameter.

---

## Scheduler V3 (8 Jobs)

| # | Job | Function | Interval | Purpose |
|---|-----|----------|----------|---------|
| 1 | Collectors | `run_all_collectors()` | 15 min | RSS + GDELT → raw_events (with source_type) |
| 2 | Dispatcher V3 | `run_dispatcher()` | 5 min | Dedup + filter + LLM + vertente routing → intake_queue |
| 3 | Fact-Checker V3 | `run_fact_checker_parallel()` | 25 min | 6 parallel sectors, dual-mode by vertente |
| 4 | Decisor Editorial | `run_editorial_decisor()` | 10 min | Deterministic gate → ready_to_write/discarded/wilson_review |
| 5 | Escritor V3 | `run_escritor()` | 30 min | 6 templates → articles (with article_type) |
| 6 | Pipeline Health | `run_pipeline_health()` | 30 min | 7 probes, V3 diagnostics, Telegram alerts |
| 7 | Coverage Analyzer | `run_coverage_analysis()` | 6 hours | Detect mainstream omissions |
| 8 | Cronistas | `run_cronistas()` | Sunday 10:00 UTC | 10 weekly chronicles |

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
- Branch naming: `type/short-description` (e.g., `feat/v3-contra-media`, `fix/fc-dual-mode`)
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

### Managing Docker Services
```bash
cd ~/noticia
docker compose ps                              # Status
docker compose logs --tail 50 pipeline         # Logs
docker compose logs --tail 50 -f pipeline      # Follow logs
docker compose build pipeline telegram-bot     # Rebuild after code changes
docker compose up -d                           # Start/restart with new images
docker compose restart telegram-collector      # Restart without rebuild (config only)
```

### CRITICAL: Code Changes Require Rebuild
```bash
# WRONG: docker compose restart (uses OLD image with OLD code)
# RIGHT:
docker compose build pipeline telegram-bot && docker compose up -d
```

### Deploying Changes
1. SSH into VM
2. `cd ~/noticia && git pull`
3. Rebuild: `docker compose build pipeline telegram-bot`
4. Restart: `docker compose up -d`
5. Verify: `docker compose ps && docker compose logs --tail 20 pipeline`

---

## Key Design Decisions

1. **Contra-media pivot (V3)** — Not generic news. Expose bias, cover omissions, verify alternatives
2. **Three vertentes** — media_watch/alt_news/editorial route through different FC modes
3. **Deterministic decisor** — No LLM in the editorial gate. Rules-based: bias → exposé, no bias → discard
4. **6 article templates** — Each article_type gets a specialized writing template with contra-media framing
5. **Coverage analyzer** — Automatic omission detection by cross-referencing sources every 6h
6. **No Chinese models in FC** — DeepSeek/Qwen/Cogito carry censorship bias. Mistral-large-3 for all FC
7. **Batch LLM over individual calls** — 10 events per LLM call reduces tokens by ~78%
8. **Deterministic pre-filtering** — Domain/keyword blocklists eliminate ~60-70% without LLM
9. **Title hash dedup** — MD5 of normalized title catches near-duplicates across sources
10. **Events retry on LLM failure** — Only mark `processed=True` after successful LLM classification
11. **Fallback web search chain** — Tavily → Exa.ai → Serper.dev ensures FC always has a search provider
12. **`.env` as single source of truth** — `sync_models_to_supabase()` propagates to agents table on startup
13. **Atomic article publication** — `publish_article_with_sources` RPC ensures consistency
14. **Wilson review escape hatch** — Ambiguous items go to Telegram for manual editorial decision

---

## Known Issues & Technical Debt

No open issues at this time.

### Resolved (March 2026)
- [x] V3 contra-media pivot implemented (4 phases)
- [x] FC dual-mode with bias_verdict and media_audit
- [x] Editorial decisor deterministic gate
- [x] 6 article templates in escritor
- [x] Coverage analyzer for omission detection
- [x] /injecta Telegram command for editorial injection
- [x] Engenheiro updated for V3 (7 probes, V3 diagnostics)
- [x] Docker images rebuilt with V3 code
- [x] 80 unit tests (pytest): dispatcher, fact-checker, escritor, models
- [x] GitHub Actions CI/CD with SSH deploy on push to main
- [x] Docker Compose with healthchecks, resource limits, auto-restart
- [x] JSON structured logging with RotatingFileHandler
- [x] healthcheck.sh (5min) + Telegram alerts
- [x] backup.sh (daily 3am, 30-day retention)
- [x] 4GB swapfile, vm.swappiness=10
- [x] Fail2Ban SSH jail (3 retries, 1h ban)
- [x] SSH key-only auth, PAT revoked
- [x] Nginx rate limiting + security headers
- [x] db_cleanup.sh (weekly, Supabase REST API)

---

*This file is read automatically by Claude. Update it when the project architecture changes.*
*Last updated: 2026-03-23 — V3 Contra-Media pivot*
