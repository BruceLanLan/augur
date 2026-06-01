# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable, all deps)
pip install -e ".[dev,all]"

# Run all tests
pytest tests/ -v

# Run a single test file or test
pytest tests/test_registry.py -v
pytest tests/test_registry.py::TestAgentRegistry::test_registry_loads_default_agents -v

# Start dashboard (port 8000)
python3 -m dashboard.app --port 8000 --cors

# Start REST API server (port 8900)
augur api --port 8900

# CLI analysis
augur analyze AAPL --persona buffett
augur consensus AAPL
augur list

# MCP server (stdio, requires Python 3.10+)
.venv/bin/augur-mcp
```

## Architecture

### Request flow

```
CLI / HTTP request
    → augur.data.fetch_market_context(ticker)
        → datasources/ provider chain (yfinance → finnhub → alphavantage → stooq)
        → returns MarketContext
    → registry.DecisionCoordinator.analyze(ticker, context)
        → 18 × BaseAgent.analyze(context) in ThreadPoolExecutor
        → each returns AgentResponse (score 0-10, signal, key_findings, coverage_confidence)
        → weighted consensus (coverage_confidence × base_weight × rolling_IC_weight)
        → returns Dict[agent_id, AgentResponse] + consensus AgentResponse
    → report.generate_report(ticker, context, results, consensus)
        → pure Markdown, no LLM calls
    → dashboard/app.py FastAPI endpoint returns JSON
```

### Key data structures (`src/augur/personas/base.py`)

- **`MarketContext`** — all numeric inputs to agents (price, PE, margins, RSI, sector, industry, `business_summary`, etc.). Rates/margins/ratios are **decimal 0-1**; market cap/FCF are **billions USD**; institutional_ownership is **0-100**.
- **`AgentResponse`** — output per agent: `score` (0-10), `signal` (SignalType enum), `key_findings`, `risks`, `coverage_confidence` (0-1, how applicable the agent's framework is to this company).
- **`BaseAgent`** — base class for all 18 personas; each implements `analyze(context) → AgentResponse`.

### Where the code actually lives

`scanner/personas/*.py` are backward-compat shims that re-export from `src/augur/personas/*.py`. The canonical implementations are all in `src/augur/`.

### `coverage_confidence` gate (critical)

Each agent sets `coverage_confidence` (0-1) reflecting how applicable its framework is. **Agents with `coverage_confidence < 0.5` are excluded from `_aggregate_items` in `report.py`** — they don't contribute their `key_findings` to the shared consensus summary. Domain-specific findings (e.g., AGI labels from Aschenbrenner, Chokepoint labels from Serenity) must be gated on `coverage_confidence >= 0.7` before being appended to `key_findings`, so they don't pollute reports for unrelated companies.

### Data source chain (`src/augur/datasources/`)

Priority: yfinance → finnhub (if `FINNHUB_API_KEY` set) → alphavantage (if `ALPHAVANTAGE_API_KEY` set) → stooq fallback. Configure optional sources via env vars (see `.env.example`). `data.py` wraps the chain with a 3-minute LRU cache (max 100 entries, evicts to 80).

### Dashboard (`dashboard/app.py`)

FastAPI app. Static files served at `/static` from `dashboard/static/`; `docs/images/` (avatars, logos) served at `/docs/images`. CSS layer: `bloomberg.css` (base terminal theme) + `ui-enhance.css` (glassmorphism overlay, do not merge these). Persona avatars are PNGs at `docs/images/avatars/{persona_id}.png`.

### Report page JS (`dashboard/templates/report_view.html`)

The voting table is parsed from Markdown. The table header regex must match `| 大师 | 流派 | 信号 |` — do NOT use `|.*大师.*|` which matches the exec-summary row `| **参与大师** |`. Column indices: `cells[0]`=name, `cells[1]`=school, `cells[2]`=signal, `cells[3]`=score ("7.5/10"), `cells[4]`=confidence. Metric extraction from the report also uses table format `key[^|]*\| value` not `key[：:] value`.

### Adding a new persona

1. Create `src/augur/personas/{id}.py` with a class extending `BaseAgent`.
2. Add a shim `scanner/personas/{id}.py` (`from augur.personas.{id} import *`).
3. Register in `AgentRegistry._register_default_agents()` in `registry.py`.
4. Add avatar PNG to `docs/images/avatars/{id}.png` (DQ1 pixel-art style, 128×128).
5. Expose metadata to the dashboard via the `PersonaInfo` builder in `dashboard/app.py`.

### Optional API tokens (`AUGUR_API_TOKEN`)

When set, all `/api/*` endpoints require `Authorization: Bearer <token>`. Leave unset for open access.
