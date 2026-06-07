.PHONY: install install-full install-mcp dev test test-fast run serve mcp api skills-gen skills-list docker-build docker-up docker-down docker-full docker-mcp clean lint format release-check help watch

PYTHON  ?= python3
PORT    ?= 8000
VERSION ?= $(shell $(PYTHON) -c "import sys; sys.path.insert(0,'src'); from augur import __version__; print(__version__)" 2>/dev/null || echo "unknown")

## ── Installation ────────────────────────────────────────────────────────────

install:           ## Install minimal (no data/MCP)
	pip install -e .

install-full:      ## Install with all extras (data + mcp + bots)
	pip install -e ".[data,mcp,telegram,slack,lark]" || pip install -e ".[data]"

install-mcp:       ## Install with MCP support (requires Python 3.10+)
	pip install -e ".[data,mcp]"

dev:               ## Install all dev dependencies
	pip install -e ".[dev,all]" 2>/dev/null || pip install -e ".[data]" && pip install pytest pytest-asyncio

## ── Running ──────────────────────────────────────────────────────────────────

serve:             ## Start dashboard at http://localhost:$(PORT)
	@echo "🦉 Augur Dashboard → http://localhost:$(PORT)"
	$(PYTHON) -m dashboard.app --port $(PORT) --host 0.0.0.0

run: serve         ## Alias for serve

mcp:               ## Start MCP server (stdio, for Hermes/Claude Desktop/OpenClaw)
	@echo "🔌 Augur MCP server starting (stdio)..."
	augur-mcp

api:               ## Start REST API server at port 8900
	augur api --port 8900

watch:             ## Watch a ticker (example: make watch TICKER=AAPL)
	augur watch $(TICKER)

## ── Skills ───────────────────────────────────────────────────────────────────

skills-gen:        ## Regenerate all Hermes/OpenClaw skill files
	$(PYTHON) scripts/generate_skills.py

skills-list:       ## List available agent skills
	augur skills

## ── Testing ──────────────────────────────────────────────────────────────────

test:              ## Run full test suite
	pytest tests/ -v

test-fast:         ## Run tests (skip slow network tests)
	pytest tests/ -q --ignore=tests/test_analyze_api_v12.py

## ── Docker ───────────────────────────────────────────────────────────────────

docker-build:      ## Build Docker image
	docker compose build

docker-up:         ## Start dashboard (detached)
	docker compose up -d dashboard

docker-down:       ## Stop all containers
	docker compose down

docker-full:       ## Start full stack (dashboard + api + cron)
	docker compose --profile api --profile cron up -d

docker-mcp:        ## Run MCP server in Docker (stdio passthrough)
	docker compose --profile mcp run --rm mcp

## ── Release ──────────────────────────────────────────────────────────────────

release-check:     ## Pre-release checklist
	@echo "Version: $(VERSION)"
	@$(PYTHON) -m pytest tests/ -q --ignore=tests/test_analyze_api_v12.py --tb=no 2>&1 | tail -3
	@echo "Skills: $$(ls skills/ | wc -l | tr -d ' ') skill directories"
	@echo "Personas: $$(ls src/augur/personas/*.py | grep -v __init__ | wc -l | tr -d ' ') persona files"

## ── Cleanup ──────────────────────────────────────────────────────────────────

## Remove build artifacts and caches
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.eggs' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ 2>/dev/null || true
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.coverage' \) -delete 2>/dev/null || true
	@echo "Clean ✓"

lint:              ## Run ruff linter (install with: pip install ruff)
	@command -v ruff &>/dev/null && ruff check src/ || echo "Install ruff: pip install ruff"

format:            ## Run ruff formatter
	@command -v ruff &>/dev/null && ruff format src/ || echo "Install ruff: pip install ruff"

## ── Help ─────────────────────────────────────────────────────────────────────

help:              ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
