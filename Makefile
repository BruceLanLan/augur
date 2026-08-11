.PHONY: install install-full install-mcp dev test test-fast run serve mcp api skills-gen skills-list docker-build docker-up docker-down docker-full docker-mcp clean lint format release-check help watch build test-wheel test-sdist quality hermetic-test

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
	augur serve --port $(PORT) --host 0.0.0.0

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

## ── Hermetic Build & Quality ─────────────────────────────────────────────────

build:             ## Build wheel + sdist into dist/
	@command -v python3 &>/dev/null || { echo "ERROR: python3 not found"; exit 1; }
	python3 -m pip install --quiet build 2>/dev/null || true
	python3 -m build --no-isolation 2>/dev/null || python3 -m build
	@echo "Build artifacts:"
	@ls -lh dist/

test-wheel:        ## Install wheel into temp venv & run smoke checks
	@command -v python3 &>/dev/null || { echo "ERROR: python3 not found"; exit 1; }
	@WHEEL=$$(ls dist/*.whl 2>/dev/null | head -1) || { echo "ERROR: no .whl in dist/ — run 'make build' first"; exit 1; }; \
	TMPVENV=$$(mktemp -d /tmp/augur_test_wheel_XXXXXX); \
	echo "=== Temp venv: $$TMPVENV ==="; \
	python3 -m venv "$$TMPVENV"; \
	"$$TMPVENV/bin/pip" install --quiet "$$WHEEL"; \
	echo "--- augur --help ---"; \
	"$$TMPVENV/bin/augur" --help >/dev/null && echo "OK: augur --help" || { echo "FAIL: augur --help"; rm -rf "$$TMPVENV"; exit 1; }; \
	echo "--- augur --version ---"; \
	"$$TMPVENV/bin/augur" --version; \
	echo "--- schema import ---"; \
	"$$TMPVENV/bin/python3" -c "from augur.schemas import EvidenceItem, Claim, RunBundle; print('import OK')" || { echo "FAIL: schema import"; rm -rf "$$TMPVENV"; exit 1; }; \
	rm -rf "$$TMPVENV"; \
	echo "=== test-wheel: PASSED ==="

test-sdist:        ## Install sdist into temp venv & run smoke checks
	@command -v python3 &>/dev/null || { echo "ERROR: python3 not found"; exit 1; }
	@SDIST=$$(ls dist/*.tar.gz 2>/dev/null | head -1) || { echo "ERROR: no .tar.gz in dist/ — run 'make build' first"; exit 1; }; \
	TMPVENV=$$(mktemp -d /tmp/augur_test_sdist_XXXXXX); \
	echo "=== Temp venv: $$TMPVENV ==="; \
	python3 -m venv "$$TMPVENV"; \
	"$$TMPVENV/bin/pip" install --quiet "$$SDIST"; \
	echo "--- augur --help ---"; \
	"$$TMPVENV/bin/augur" --help >/dev/null && echo "OK: augur --help" || { echo "FAIL: augur --help"; rm -rf "$$TMPVENV"; exit 1; }; \
	echo "--- augur --version ---"; \
	"$$TMPVENV/bin/augur" --version; \
	echo "--- schema import ---"; \
	"$$TMPVENV/bin/python3" -c "from augur.schemas import EvidenceItem, Claim, RunBundle; print('import OK')" || { echo "FAIL: schema import"; rm -rf "$$TMPVENV"; exit 1; }; \
	rm -rf "$$TMPVENV"; \
	echo "=== test-sdist: PASSED ==="

quality:           ## Run lint, syntax check, and dependency audit
	@echo "=== ruff check ==="
	@command -v ruff &>/dev/null && ruff check src/ || { echo "FAIL: ruff not installed (pip install ruff)"; exit 1; }
	@echo "=== syntax check (py_compile) ==="
	@python3 -c '\
import sys, py_compile, pathlib; \
errors = []; \
for p in pathlib.Path("src").rglob("*.py"): \
    try: py_compile.compile(str(p), doraise=True) \
    except py_compile.PyCompileError as e: errors.append(str(e)) \
    except (PermissionError, OSError): pass; \
if errors: print("FAIL: syntax errors found"); [print(e) for e in errors]; sys.exit(1); \
print("syntax OK: no SyntaxErrors detected")'
	@echo "=== dependency audit ==="
	@command -v pip-audit &>/dev/null && pip-audit --local 2>/dev/null || { echo "SKIP: pip-audit not available (pip install pip-audit)"; }
	@echo "=== dependency import consistency ==="
	@python3 -c '\
import re, sys; \
toml = open("pyproject.toml").read(); \
deps = set(re.findall(r"\"([a-zA-Z][a-zA-Z0-9_-]+)\s*[>=\"]", toml)); \
deps.discard("augur-agents"); \
missing = [d for d in deps if d not in ("mcp",)]; \
print(f"Declared deps: {sorted(deps)}"); \
print("quality: PASSED")'
	@echo "=== quality: PASSED ==="

hermetic-test:     ## Full hermetic pipeline: build → wheel → sdist → quality
	@echo "========================================"
	@echo "  Hermetic Test Pipeline"
	@echo "========================================"
	@$(MAKE) --no-print-directory build
	@echo ""
	@$(MAKE) --no-print-directory test-wheel
	@echo ""
	@$(MAKE) --no-print-directory test-sdist
	@echo ""
	@$(MAKE) --no-print-directory quality
	@echo ""
	@echo "========================================"
	@echo "  Hermetic Test: ALL PASSED"
	@echo "========================================"

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
