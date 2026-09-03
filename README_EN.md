[🇨🇳 中文](README.md) | 🇺🇸 English

<div align="center">

<img src="docs/images/en/hero-banner.png" alt="Augur — Research Memory System" width="100%">

# 🦉 Augur

**Not another AI stock picker. A research memory system that remembers what you knew, when you knew it, what changed, and who disagrees — and why.**

[![v11.0.0-rc1](https://img.shields.io/badge/v11.0.0--rc1-Latest-ff6b35?style=for-the-badge)](https://github.com/BruceLanLan/augur-next)
[![3422 Tests](https://img.shields.io/badge/3426_Tests-Passing-brightgreen?style=for-the-badge)](https://github.com/BruceLanLan/augur-next/actions)
[![Evidence-First](https://img.shields.io/badge/Evidence-First_📋-4a90d9?style=for-the-badge)](#-why-augur)
[![18 Masters](https://img.shields.io/badge/18-Masters-gold?style=for-the-badge)](#-18-investment-masters)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude_%2F_Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![Local-First](https://img.shields.io/badge/Local--First_🔒-blue?style=for-the-badge)](#-quick-start)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 🤔 Why Augur

Most AI finance tools give you an answer. Augur gives you **verifiable research artifacts**.

| | Generic AI Tool | Augur |
|---|---|---|
| What you get | "On one hand… on the other… invest at your own risk" | 18 independent judgments + where they agree and clash |
| Data provenance | Unknown. Possibly training data | Every conclusion: source locator — SEC filing URL, accession number, retrieval time |
| Missing data | Silently filled with 0 | Explicitly `missing`. Dependent masters `abstain` with reason |
| Look back in 3 months | No memory | RunBundle: immutable input snapshot, step results, coverage stats. Diff to see exactly what changed |
| Your data | Cloud. Unknown access | Local. `~/.augur`. You control everything |

**Augur doesn't make decisions for you. It builds your evidence trail.**

---

## 🚀 Quick Start

```bash
git clone https://github.com/BruceLanLan/augur-next.git && cd augur-next
pip install -e ".[data]"

export AUGUR_DATA_DIR=$(pwd)/.augur_dev   # isolated data root

augur serve --open          # Dashboard · ⌘K for command palette
```

Or CLI-only:

```bash
augur analyze AAPL          # 18 masters
augur workflow TSLA         # 6-stage pipeline
augur export AAPL --format md  # Export Markdown report
```

---

## ✨ What's New in v11

v11 is a **foundation rebuild** — from "AI report generator" to "Research Memory System."

### 14 New Modules

| Module | Purpose |
|---|---|
| `thesis.py` | Thesis Journal + ThesisDelta + DecisionLog — track, update, and review your investment theses |
| `valuation.py` | DCF + WACC + Scenario Lab — pure `decimal.Decimal`, LLM never touches arithmetic |
| `disagreement.py` | Distill 18 persona outputs into 3-5 decision-relevant conflicts |
| `filing_delta.py` | Compare 20+ financial metrics, text sections, and guidance between SEC filings |
| `guidance_tracker.py` | Track management guidance ranges across quarters, compute accuracy |
| `research_inbox.py` | Aggregate events into a prioritized research queue |
| `risk_review.py` | Risk factor categorization + covenant compliance review |
| `eval_lab.py` | Walk-forward OOS evaluation + persona ablation |
| `export.py` | Markdown / PDF / JSON / Evidence Pack export |
| `earnings.py` | Earnings event detection + dossier readiness |
| `run_tracker.py` | StepResult wrapper + checkpoint save/resume |
| `provenance.py` | ProvenanceBlock — source, freshness, degradation metadata |
| `capability.py` | Capability Registry with budget/timeout control |
| `schemas/` | EvidenceItem / Claim / StepResult / RunBundle / SkillSpec v1 |

### Key Improvements

1. **Missing data is no longer zero** — ownership fields are `None`, not `0`. 11 personas explicitly abstain.
2. **Three time semantics** — `effective_at` / `available_at` / `retrieved_at`. No look-ahead bias.
3. **Immutable RunBundle** — every run snapshotted. Checkpoint resume. Diff between runs.
4. **Declarative Skills** — pure YAML. No `module_path`, `shell`, or `import`. Runtime permission enforcement.
5. **UI/UX** — ⌘K Command Palette · Dark Mode · Evidence Graph (force-directed) · Thesis Journal page · Skeleton/Empty-state/Toast · Responsive
6. **3426 tests** — hermetic, zero user-directory pollution. PBKDF2 600k. SQLite WAL + corruption backup.

Full details → [docs/RELEASE_NOTES_v11.md](docs/RELEASE_NOTES_v11.md)

---

## 📊 Dashboard

| Page | Path | Feature |
|---|---|---|
| Home | `/` | Real-time quotes + master overview |
| Stock Analysis | `/stocks` | 18 masters analyze one ticker |
| Committee | `/committee` | 5 presets + custom combinations |
| Debate | `/debate` | Structured bull vs bear |
| **Thesis Journal** | `/thesis` | 🆕 Create, track, review investment theses |
| History | `/history` | 52-week heatmap |
| Portfolio | `/portfolio` | Kelly position sizing |
| Watchlist | `/watchlist` | Batch management + cron scheduling |

---

## 🎭 18 Investment Masters

| School | Masters |
|---|---|
| 🏦 Value | Buffett · Graham · Munger · Fisher |
| 🚀 Growth | Lynch · Cathie Wood · Thiel · Aschenbrenner |
| 🌍 Macro | Dalio · Soros · Marks · ARPS |
| 🇨🇳 China Value | Duan Yongping · Zhang Lei · Li Lu · Dan Bin · Dayu |
| ⚙️ Special | Serenity (AI supply chain) |

---

## 🔌 Integrations

| Platform | Method |
|------|---------|
| **Web Dashboard** | `augur serve` |
| **Claude Desktop** | MCP → `augur mcp-server` |
| **External Agents** | `augur://evidence/{id}` · `augur://runs/{id}` |

---

## 💻 CLI Commands

```bash
# Analysis
augur analyze AAPL · augur workflow TSLA · augur committee AAPL

# Export (v11)
augur export AAPL --format md | pdf | evidence-pack

# Skills (v11)
augur skill run earnings-prep --ticker AAPL
augur skill run filing-delta --ticker AAPL

# Valuation (v11)
augur valuation AAPL

# Data
augur fetch AAPL · augur sentiment AAPL · augur backtest AAPL

# Dashboard · Monitor · Bots
augur serve · augur watch · augur cron-run · augur telegram
```

---

## 🗺️ Docs

| Document | Content |
|---|---|
| [ROADMAP.md](docs/ROADMAP.md) | 7-day v11 RC sprint + backlog |
| [PRODUCT_DIRECTIONS.md](docs/PRODUCT_DIRECTIONS.md) | Product direction + feature map |
| [DIFFERENTIATION_STRATEGY.md](docs/DIFFERENTIATION_STRATEGY.md) | Competitive differentiation |
| [RELEASE_NOTES_v11.md](docs/RELEASE_NOTES_v11.md) | Full release notes + migration guide |
| [schema-reference.md](docs/schema-reference.md) | Schema field reference |
| [skills-guide.md](docs/skills-guide.md) | Skill tutorial + security model |

---

## 🏗️ Project Status & Dev Guide

**Status**: v11.0.0-rc1 code-complete, awaiting owner release decision.

| Status | Item |
|---|---|
| ✅ | 3426 passed locally (2026-09-03, python 3.12) · `ruff check src/` clean (rule set now pinned) |
| 🔧 | CI `Tests` was a false green from 08-12 (`\| tail` swallowed the exit code + missing `jsonschema`), `Hermetic Smoke` was red since creation (bare `ruff`) — both fixed, awaiting the next push for a real `N passed` |
| 🔧 | R6 learned-weight 60/40 blend is now opt-in (`AUGUR_FORCE_LEARNED=1`) until an owner-approved gate exists |
| ✅ | wheel/sdist build + fresh-venv dual-format smoke verified locally |
| ✅ | [ROADMAP](docs/ROADMAP.md) backlog (20 items) complete at code level |
| ⏳ | TestPyPI / fresh-install run — needs PyPI credentials (owner) |
| ⏳ | Design-partner validation — needs real users (owner) |
| ⏳ | Public release — `v*` tag triggers `publish.yml` (owner decision) |

### Local dev & test

```bash
# ⚠️ On this machine `python` is 2.7 — use python3 (3.9+)
# ⚠️ `import augur` resolves to a stale editable install; add PYTHONPATH=src

PYTHONPATH=src python3 -m pytest tests/ -q        # full suite (~3.5 min)
python3 -m ruff check src/                         # lint (0 errors)
make build && make test-wheel && make test-sdist   # build + smoke
PYTHONPATH=src python3 scripts/deployment_check.py
```

> Handoff notes: [CHANGELOG.md](CHANGELOG.md) "Round 8 Finalization" & [docs/RELEASE_NOTES_v11.md](docs/RELEASE_NOTES_v11.md).

---

## 📝 Changelog

<details open>
<summary><strong>v11.0.0-rc1 — Research Memory System (current)</strong></summary>

Foundation rebuild: 3426 tests · 24 new modules.

- Schema contracts: EvidenceItem (three-time), Claim, StepResult, RunBundle, SkillSpec v1
- Research loop: Thesis Journal → Filing Delta → Disagreement Map → Guidance Tracker → Research Inbox
- Valuation engine: pure Decimal DCF + WACC + Scenario Lab
- Eval: Chronological Evaluation Lab + Persona Ablation + OOS harness
- UI: ⌘K palette · dark mode · evidence graph · thesis page · skeleton/empty-state
- Trust: PBKDF2 600k · SQLite WAL · calibration labels · 3426 hermetic tests
</details>

<details>
<summary><strong>v10.x and earlier</strong></summary>

v10: Bloomberg-style terminal, 6-stage workflow, 13 MCP tools · v9: Hermes Agent · v8: HD-2D design system
</details>

---

<div align="center">

MIT License · Built with ❤️ by <a href="https://github.com/BruceLanLan">BruceLanLan</a>

*For educational and research purposes only. Not investment advice.*

</div>
