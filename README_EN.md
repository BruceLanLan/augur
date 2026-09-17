[🇨🇳 中文](README.md) | 🇺🇸 English

<div align="center">

<img src="docs/images/en/hero-banner.png" alt="Augur — Research Memory System" width="100%">

# 🦉 Augur

**Not another AI stock picker. A local research memory system that remembers what you knew, when you knew it, what changed, and who disagrees — and why.**

[![v11.0.0-rc1](https://img.shields.io/badge/v11.0.0--rc1-Release_Candidate-ff6b35?style=for-the-badge)](CHANGELOG.md)
[![Tests](https://img.shields.io/github/actions/workflow/status/BruceLanLan/augur/tests.yml?branch=main&label=tests&style=for-the-badge)](https://github.com/BruceLanLan/augur/actions/workflows/tests.yml)
[![18 Masters](https://img.shields.io/badge/18-Masters-gold?style=for-the-badge)](#-18-investment-masters)
[![MCP](https://img.shields.io/badge/MCP-1.x_%2F_2.x-orange?style=for-the-badge)](#-claude--agent-integration)
[![Local-First](https://img.shields.io/badge/Local--First_🔒-blue?style=for-the-badge)](#-data--privacy)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

> ⚠️ **For research and education only. Not investment advice.** The masters are rule-based simulations of publicly known investment philosophies, not the views of those people. Every score, Kelly size and valuation depends on data quality and model assumptions.

---

## 🤔 Why Augur

Most AI finance tools give you an answer. Augur gives you **research artifacts you can check later**.

| | Typical AI tool | Augur |
|---|---|---|
| What you get | "On one hand… on the other…" | 18 independent persona verdicts, where they agree and where they fight |
| Where data came from | Unclear | Every evidence item carries its source, business time, availability time and retrieval time |
| Missing data | Silently zero | Marked `missing`; personas that need the field `abstain` and say why |
| Three months later | No memory | Each run is an immutable RunBundle you can export, compare and audit |
| Where your data lives | Someone's cloud | Locally in `~/.augur` (override with `AUGUR_DATA_DIR`), no telemetry |

---

## 🚀 Quick Start (5 minutes)

Python 3.9+ (MCP needs 3.10+).

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[data]"            # core + live yfinance data
# optional: pip install -e ".[data,mcp]"  MCP server
#           pip install -e ".[export]"    PDF export

# SEC EDGAR requires a real contact address in requests (US fundamentals)
export AUGUR_EDGAR_CONTACT_EMAIL="you@example.com"
```

**Dashboard:**

```bash
augur serve --open                 # http://localhost:8000 · ⌘K command palette
```

**CLI research loop** (every command below was verified on a fresh install):

```bash
augur analyze AAPL                 # 18 masters + weighted consensus + Kelly size
augur workflow AAPL                # tracked pipeline, saves a RunBundle, prints the Run ID
augur research-report AAPL         # from the latest run: consensus, disagreement map, provenance
augur export AAPL --format md      # export the latest run (md / json / evidence-pack / pdf)
augur committee AAPL --preset value -q "Is the moat widening or narrowing?"
augur valuation AAPL               # two-stage DCF, auto-fills FCF/shares/net debt and says so
```

Offline? `augur analyze NVDA --pe 60 --roe 0.45` takes manual metrics; `augur backtest AAPL --demo` uses synthetic data.

---

## 🔄 Upgrading from v10

The previous public release was v10.15.0. v11 is a **trust and research-foundation** release, not new personas or pages. Behaviour changes to know about:

| Change | Effect | What to do |
|---|---|---|
| `insider_ownership` / `institutional_ownership` go from `0` to `Optional[float]` | Missing values are `None`; the 11 personas that use them abstain | Handle `None` in custom code |
| Rolling-IC weights are no longer blended by default | Only applied when calibration status is `validated-calibrated` | `AUGUR_FORCE_RIC=1` to experiment |
| Learned (R6) weights are no longer blended by default | With little data they turn noise into "skill" | `AUGUR_FORCE_LEARNED=1` to experiment |
| SEC EDGAR market cap is now in billions of USD | The overlay used to return raw USD, distorting size and FCF-yield checks; **replay-derived factor/IC results produced before v11 carry that error** | Regenerate replay artifacts if you rely on them |
| `augur serve` / `augur api` bind to `127.0.0.1` by default | Not reachable from the LAN out of the box | Set `AUGUR_API_TOKEN`, then pass `--host 0.0.0.0` |
| Legacy replay records without `field_availability` are rejected | Clear error instead of silent loading | Regenerate |
| Minimum Python 3.9; MCP works with `mcp` 1.x and 2.x | — | — |

Full details: [docs/RELEASE_NOTES_v11.md](docs/RELEASE_NOTES_v11.md) and [CHANGELOG.md](CHANGELOG.md).

---

## 🎭 18 Investment Masters

> Rule-based portraits of investment philosophies across value, growth, macro and Chinese markets. Chinese masters answer in Chinese.

| School | Masters |
|--------|---------|
| 🏦 Classic Value | Warren Buffett · Benjamin Graham · Charlie Munger · Philip Fisher |
| 🚀 Growth & Innovation | Peter Lynch · Cathie Wood · Peter Thiel · Leopold Aschenbrenner |
| 🌍 Macro & Cycles | Ray Dalio · George Soros · Howard Marks · ARPS (crypto/gold) |
| 🇨🇳 Chinese Value | Duan Yongping · Zhang Lei · Li Lu · Dan Bin · Dayu |
| ⚙️ Special | Serenity (AI compute supply chain) |

The consensus engine weights by confidence, data coverage and sector relevance, and outputs a signal, score, confidence and Kelly position size. `augur list-personas` shows all IDs.

---

## 📊 Dashboard

Run `augur serve`, then open http://localhost:8000.

| Page | Path | What it does |
|---|---|---|
| Home | `/` | Market tape + masters overview |
| Stock analysis | `/stocks` | Enter a ticker, 18 masters analyze it |
| Committee / Debate / Compare | `/committee` · `/debate` · `/compare` | Preset committees, multi-round debate, radar comparison |
| History | `/history` | Run history and heatmap |
| Thesis Journal | `/thesis` | Theses, falsification conditions, decision log |
| Earnings | `/earnings` · `/scorecard` | Earnings queue, post-earnings scorecard |
| Research inbox | `/inbox` | Aggregated items needing attention |
| Valuation lab | `/valuation` | DCF inputs + sensitivity grid |
| Portfolio / Watchlist / Settings | `/portfolio` · `/watchlist` · `/settings` | Kelly allocation, scheduled analysis, layout and persona subsets |

---

## 🔌 Claude / Agent Integration

The MCP server exposes 13 tools, 7 research prompts and 5 read-only resource types (`augur://evidence/{id}`, `augur://runs/{id}`, `augur://thesis/{id}`, `augur://decisions/{id}`, `augur://ledger/{ticker}/{quarter}`). It was verified with real stdio client sessions on both `mcp` 1.x and 2.x.

```bash
pip install -e ".[data,mcp]"
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp", "env": { "AUGUR_EDGAR_CONTACT_EMAIL": "you@example.com" } }
  }
}
```

There are also Hermes / OpenClaw skill packs (`src/skills/`, see [docs/hermes-setup-guide.md](docs/hermes-setup-guide.md)) and Telegram / Slack / Lark / WeChat bot entry points.

---

## 💻 CLI Cheat Sheet

```bash
# Analysis
augur analyze AAPL [--persona buffett] [--json]
augur workflow TSLA --steps fetch,analyze,consensus,committee,debate,sentiment
augur committee NVDA --agents buffett,munger,dalio
augur batch AAPL MSFT NVDA

# Research artifacts
augur research-report AAPL [--format json]
augur export AAPL --format md|json|evidence-pack|pdf [-o PATH] [--run-id ...]
augur dossier AAPL                  # pre-earnings dossier
augur valuation AAPL [--fcf 100e9 --shares 15e9 --growth 0.08 --wacc 0.10]
augur filing-delta AAPL --new q3.json --prev q2.json

# Data
augur fetch AAPL · augur sentiment AAPL · augur insider AAPL · augur earnings --days 30
augur backtest AAPL --days 60 [--demo] · augur ic-report · augur doctor

# Monitoring & servers
augur watch AAPL NVDA --interval 60 · augur watchlist-add AAPL · augur cron-run
augur serve [--port 8000] · augur mcp-server · augur skills
```

`augur --help` lists all 39 subcommands.

---

## 🧭 Feature Maturity

Stated plainly, so "there is code for it" is not mistaken for "it works".

| Status | Scope |
|---|---|
| **Stable** | 18-persona analysis and consensus, the CLI research loop above, main dashboard pages, MCP server, RunBundles and export, the data-source chain (yfinance → SEC EDGAR overlay) |
| **Works, with limits** | Disagreement-map "conflict points" are template statements chosen from the signal split, not derived claim-by-claim from evidence; `augur guidance` needs `AUGUR_EDGAR_GUIDANCE_EXTRACTION=1` and calls a paid LLM; PDF export needs the `[export]` extra |
| **Experimental (off by default)** | Rolling-IC dynamic weights (`AUGUR_FORCE_RIC=1`), learned weights (`AUGUR_FORCE_LEARNED=1`) — neither has passed a pre-registered out-of-sample test |
| **Library code with no user entry point yet** | `citation_queue`, `cost_budget`, `eval_lab`, `outcome_tracker`, `pack_digest`, `prompt_eval`, `review_comment`, `risk_review`, `team_audit`; the skill runner (manifests and permission checks exist, but there is no `augur skill run`; see [docs/skills-guide.md](docs/skills-guide.md)) |

---

## 🔒 Data & Privacy

- All state lives in a local data directory (`~/.augur` by default, `AUGUR_DATA_DIR` to change it). No telemetry. Single-user with no sign-up by default (optional multi-user mode via `AUGUR_MULTI_USER=1`).
- Network requests Augur makes: market and fundamentals data (yfinance, SEC EDGAR); optional LLM calls, only when you configure a key and enable the feature; dashboard pages load Chart.js from the jsDelivr CDN.
- The dashboard listens on localhost only by default. Set `AUGUR_API_TOKEN` before exposing it; see [docs/self-hosted-guide.md](docs/self-hosted-guide.md).

Key environment variables:

| Variable | Purpose |
|---|---|
| `AUGUR_DATA_DIR` | Data directory |
| `AUGUR_EDGAR_CONTACT_EMAIL` | Contact address SEC EDGAR requires (a placeholder with a warning is used if unset) |
| `AUGUR_API_TOKEN` / `AUGUR_MULTI_USER` | Dashboard `/api/*` authentication |
| `AUGUR_CORS_ORIGINS` | Allowed CORS origins |
| `AUGUR_FORCE_RIC` / `AUGUR_FORCE_LEARNED` | Turn on experimental dynamic weights |
| `AUGUR_SKIP_MACRO_FETCH` | Skip the VIX/SPY macro fetch (offline or CI) |
| `AUGUR_EDGAR_GUIDANCE_EXTRACTION` | Enable LLM-based guidance extraction (paid) |

---

## 🏗️ Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,data,mcp]" "ruff>=0.16,<0.17" build

make verify     # full test suite + ruff + wheel/sdist build with sha256 digests
make lint       # ruff (rule set pinned to E4/E7/E9/F)
make test-wheel # install the built wheel into a fresh venv and smoke-test it
```

- Tests run against a temporary `AUGUR_DATA_DIR`, never write to your `~/.augur`, and pass with the network fully blocked.
- CI (`.github/workflows/`): `Tests` runs the full suite on Python 3.9 / 3.11 / 3.12 and asserts the collected test count; `Hermetic Smoke` installs from the wheel and the sdist into fresh venvs and runs ruff and pip-audit.
- See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🗺️ Docs & Roadmap

| Document | Contents |
|---|---|
| [docs/ROADMAP.md](docs/ROADMAP.md) | The single authoritative roadmap: v11 RC → GA steps, definition of done, open decisions (Chinese) |
| [docs/RELEASE_NOTES_v11.md](docs/RELEASE_NOTES_v11.md) | v11 release notes and migration guide |
| [docs/reviews/](docs/reviews/) | Project reviews, each finding with its evidence level and fix (Chinese) |
| [docs/schema-reference.md](docs/schema-reference.md) | EvidenceItem / Claim / StepResult / RunBundle / SkillSpec |
| [docs/api-reference-v11.md](docs/api-reference-v11.md) | Python API / REST / MCP |
| [docs/examples.md](docs/examples.md) | Worked examples |
| [docs/self-hosted-guide.md](docs/self-hosted-guide.md) | Docker / systemd / reverse proxy / auth |
| [docs/INDEX.md](docs/INDEX.md) | Full documentation index |

---

## 📝 Changelog

<details open>
<summary><strong>v11.0.0-rc1 — Research Memory System (current)</strong></summary>

- **Research foundation**: EvidenceItem with three time semantics, Claim, StepResult, immutable RunBundle, declarative SkillSpec v1
- **Research loop**: Thesis Journal, Filing Delta, disagreement map, Guidance Tracker, research inbox, DCF valuation lab
- **Trust**: missing data propagated explicitly, calibration status labels, unvalidated dynamic weights off by default
- **Fixes found by running everything from a fresh install before the public release**: `workflow` checkpoint crash, evidence timestamp timezone bug, `export` / `research-report` / `dossier` wired to real runs, `committee` crash, SEC EDGAR market cap off by 10⁹, valuation inventing inputs, servers exposed on the LAN by default, avatars 404 in pip installs, MCP support for `mcp` 2.x, CI false-green fixed

See [CHANGELOG.md](CHANGELOG.md).
</details>

<details>
<summary><strong>v10.15.0 — public sync release</strong></summary>

Real SEC EDGAR fundamentals, three credibility fixes, `augur doctor` environment diagnostics.
</details>

<details>
<summary><strong>v10.0.0 and earlier</strong></summary>

v10: Bloomberg-style terminal + workflows + MCP tools · v9: Hermes Agent + committees · v8: HD-2D design system
</details>

---

<div align="center">

MIT License · Created by [BruceLanLan](https://github.com/BruceLanLan) (X: [@BruceBlue](https://x.com/BruceBlue))

*For research and education only. Not investment advice.*

</div>
