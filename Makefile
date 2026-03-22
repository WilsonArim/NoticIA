# ──────────────────────────────────────────────────────────────────────────────
# NoticIA — Monorepo Makefile
# ──────────────────────────────────────────────────────────────────────────────
# Usage:  make <target>
#
# Shortcuts for the most common development and operations tasks across
# all three services (frontend, pipeline, telegram-bot/collector).
# ──────────────────────────────────────────────────────────────────────────────

.PHONY: help up down restart logs ps build test lint typecheck deploy clean

COMPOSE = docker compose

# ── Default ──────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── Docker ───────────────────────────────────────────────────────────────────

up: ## Start all services (detached)
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

build: ## Rebuild all Docker images
	$(COMPOSE) build

ps: ## Show running containers
	$(COMPOSE) ps

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-pipeline: ## Tail pipeline logs only
	$(COMPOSE) logs -f --tail=100 pipeline

logs-bot: ## Tail telegram-bot logs only
	$(COMPOSE) logs -f --tail=100 telegram-bot

logs-collector: ## Tail telegram-collector logs only
	$(COMPOSE) logs -f --tail=100 telegram-collector

# ── Testing ──────────────────────────────────────────────────────────────────

test: ## Run pipeline unit tests
	cd pipeline && PYTHONPATH=src python3 -m pytest src/openclaw/tests/ -v --tb=short

test-quick: ## Run pipeline tests (no verbose)
	cd pipeline && PYTHONPATH=src python3 -m pytest src/openclaw/tests/ -q

# ── Linting ──────────────────────────────────────────────────────────────────

lint: ## Lint all code (frontend + pipeline)
	@echo "── Frontend (ESLint) ──"
	npx eslint . --max-warnings=0 || true
	@echo ""
	@echo "── Pipeline (Ruff) ──"
	cd pipeline && python3 -m ruff check src/ || true

typecheck: ## Type-check all code
	@echo "── Frontend (TypeScript) ──"
	npx tsc --noEmit || true
	@echo ""
	@echo "── Pipeline (mypy) ──"
	cd pipeline && python3 -m mypy src/openclaw/ --ignore-missing-imports || true

fmt: ## Auto-format pipeline code
	cd pipeline && python3 -m ruff format src/
	cd pipeline && python3 -m ruff check --fix src/ || true

# ── Deploy ───────────────────────────────────────────────────────────────────

deploy: ## Full deploy: pull, rebuild, restart
	git pull
	$(COMPOSE) build
	$(COMPOSE) up -d

# ── Maintenance ──────────────────────────────────────────────────────────────

clean: ## Remove Docker build cache and dangling images
	docker system prune -f
	docker builder prune -f

health: ## Check health of all containers
	@$(COMPOSE) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

disk: ## Show disk usage by Docker
	docker system df
