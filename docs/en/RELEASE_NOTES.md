# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

---

## v10.13.0 — Factor-level attribution analysis (research script) (2026-07-14)

The 18 masters each carry roughly 70-90 named judgment factors under the
hood (Buffett's "moat", Graham's "margin of safety"), but nobody had
systematically checked which of these actually predict future returns
versus which just sound plausible. This release adds a research script
that computes a cross-sectional predictive-power score (rank-IC) for each
factor individually against real historical filing data, with a built-in
"check both halves of the window separately" safeguard -- only factors
that agree in direction and clear a minimum strength in both halves count
as stable candidates; everything else, even if it looks strong over the
whole window, gets explicitly flagged as "possibly coincidence, not a
conclusion." This discipline exists because the project got burned by
exactly this trap before: the regime-weight multipliers looked fine over
one full window and only fell apart once checked half-by-half.

This is a research script (`scripts/factor_attribution.py`), not a feature
wired into the automatic analysis pipeline -- it's run manually, and a
full real-data run takes tens of minutes.

## v10.12.0 — Weekly real-network data-source smoke test (2026-07-14)

The stooq data-source breakage found earlier (2026-07-09) was pure luck --
noticed by hand while debugging something else. This release adds a
GitHub Actions job that runs every Monday and makes real network requests
against SEC EDGAR and yfinance: an EDGAR failure fails the job (SEC rarely
rate-limits CI runner IPs, so a failure there is a real signal); a yfinance
failure only warns without failing the job (Yahoo Finance blocking/
rate-limiting cloud IP ranges is common enough that failing the build on it
would just create alert fatigue, not catch real regressions). Breakage like
this should now surface on its own instead of depending on luck.

## v10.11.0 — Data-source connectivity history (2026-07-12)

The previous release's `augur doctor` could only show whether a data source was reachable *right now*, with no trend. This release has every `augur doctor` run record that probe's outcome to a small local history file (`~/.augur/provider_stats.json`, local-only, nothing phoned home), keeping the last 7 days. A dead endpoint like stooq's would now show up in `augur doctor`'s output as "0/7 reachable this week" instead of requiring someone to notice by accident.

## v10.10.0 — augur doctor environment check (2026-07-12)

Diagnosing local environment problems used to be guesswork -- in fact, development on the previous release ran straight into one: a machine whose Python was linked against Apple's LibreSSL instead of real OpenSSL, which silently broke every yfinance request with no indication of why, and took manual step-by-step digging to track down. This release adds an `augur doctor` command that checks for exactly this class of problem in one shot:

- Whether the Python/SSL toolchain is a known-bad combination for yfinance (with a fix suggestion)
- Whether optional config like FINNHUB / Alpha Vantage / OpenAI keys and the EDGAR contact email are set
- Whether each data source (yfinance / finnhub / alphavantage / stooq) is actually reachable right now
- How many predictions the learning engine has accumulated and how many have been resolved

Pass `--offline` to skip the network checks.

## v10.9.0 — Credibility overhaul + real SEC EDGAR data (2026-07-09)

No flashy new UI in this release — instead, a top-to-bottom pass on "how much should you actually trust these 18 masters' scores," from the consensus math itself, to whether the learning loop was ever really learning, to whether the fundamentals feeding every persona were real. Everything that could be verified against real data was.

### Consensus scores are no longer quietly diluted by half

A default-on "MetaModel" used to blend the masters' carefully weighted score 50/50 with a plain median — cutting the weight of their actual judgment in half, and it had never been validated as an improvement in the first place. That default weight is now zero, so the consensus score you see actually reflects the weighting differences between masters.

### Backtests no longer default to fake data

The Dashboard's Backtest page and the `augur backtest` CLI command used to default to programmatically generated synthetic data that looked like a real backtest result but wasn't. Real historical data is now the default; synthetic data is still available but requires an explicit `--demo` flag and is clearly labeled "demo data, not counted on the leaderboard."

### The learning loop actually accumulates data now

Augur has advertised "the masters get more accurate the more you use it" since v8, but the underlying learning mechanism never actually accumulated real data — predictions weren't persisted, and nothing ever checked back on what actually happened. Predictions are now persisted immediately, and a scheduled job automatically resolves predictions once they're due. Starting today, you'll see the first real "prediction accuracy" numbers in roughly 30 days.

### SEC EDGAR: real filings, not simplified ratios

The PE, ROE, gross margin, etc. that all 18 masters see used to come from yfinance's simplified calculations. They now come from the U.S. Securities and Exchange Commission's official EDGAR filings (real numbers straight out of 10-K/10-Q reports), with historical depth extended from roughly 2022 back to around 2011 depending on the company. This doesn't change how you call `augur analyze`/`augur consensus` — just how real the numbers behind it are. (US-listed tickers and US-listed Chinese ADRs only; A-shares, Hong Kong stocks, and crypto are unaffected and keep using the existing data source.)

The same SEC pipeline also unlocks two new signals every master can optionally draw on:

- **Insider buying signal**: tracks executives'/directors' real open-market buy/sell activity over the trailing 90 days (excluding RSU vesting and tax-withholding noise), with clustered buying amplified.
- **Institutional flow signal**: tracks quarter-over-quarter position changes at well-known institutions like Berkshire Hathaway, Renaissance Technologies, and Bridgewater Associates.

### New (opt-in): AI reads the filing and extracts management's outlook

New `augur guidance TICKER` command: an LLM reads the "Management's Discussion and Analysis" section of a company's latest 10-K/10-Q and extracts management's outlook sentiment (positive/negative/neutral), any explicit forward guidance numbers, and notable risk-factor language. Since this makes real, billable LLM API calls, it's **off by default** — set `AUGUR_EDGAR_GUIDANCE_EXTRACTION=1` to opt in, and it only ever runs when you explicitly call it (no automatic runs, no push notifications).

### Sentiment analysis fix

The "X (Twitter)" component of social sentiment analysis had always been a fake placeholder (X's API access was never actually available) but still carried a 20% weight in the score. It's now fully removed from the calculation; StockTwits and Reddit (the two real data sources) absorb that weight proportionally.

### Regime weights: honestly retired after validation

Earlier versions had a set of hand-picked rules for shifting master weights based on bull/bear market regime (e.g. "trust Howard Marks more in a bear market"), and those specific numbers had never been validated against real historical data. A real out-of-sample validation across 4 years and 37 stocks was run using the new SEC data, and the honest finding was: **no clear benefit observed**. Rather than keep an unvalidated rule quietly shaping your consensus score, it's been disabled.

### Internal engineering health

The CLI (`cli.py`) was split from a single 1476-line file into 9 purpose-grouped modules. Purely internal — doesn't change how any command is used.

---

## v10.0.0 — Public launch (2026-06-29)

This is the first official public release of **Augur v10**. The v8.2→v10.0 jump is a full-stack upgrade.

### Terminal Workspace (Bloomberg Terminal style)

The `/settings` page gains a complete layout system so you can make the Dashboard your own:

- **4 layout presets**: `analyst` (default, full features) / `trader` (minimal, fastest signal) / `committee` (committee-centric) / `minimal` (most nav hidden). Switching preset changes the default landing page, Ticker Tape toggle, and which nav items are visible.
- **Multiple named profiles**: save several workspace configs and switch between them without losing the others — e.g. "day trading" and "weekend deep research" can be completely different setups.
- **Enabled-master subset**: tick only the masters you trust in Settings; the consensus system renormalizes weights among only those masters — not a simple equal split, but a proper redistribution.
- **Committee preset bound to profile**: switching profiles also switches your default committee lineup.
- Persisted in `~/.augur/workspace.yaml`, with export/import — take your setup to a new machine.

### Agents can operate your terminal

Any MCP client (Claude Desktop, Hermes, OpenClaw, Claude Code) can now read and modify your workspace config directly — no manual Dashboard clicks needed:

- `mcp_augur_workspace_get` — read your current terminal layout and enabled masters
- `mcp_augur_workspace_set` — let an agent switch your preset, update your committee lineup, etc.
- `mcp_augur_workspace_profiles` — list, create, delete, switch profiles

### `augur_workflow` — full analysis chain in one call

```bash
augur workflow NVDA --steps fetch,analyze,consensus,committee
```

Or via MCP: `mcp_augur_workflow`. A single call chains `fetch → analyze → consensus → committee → debate → sentiment`. Any step that fails records its error and the chain continues. Default steps follow your layout preset — `trader` mode defaults to `fetch,consensus` only (faster), `committee` mode adds `committee`.

### WebSocket real-time streaming

- **`/ws/workspace`**: get the current workspace state on connect, then live-push updates whenever any client (Dashboard or MCP) changes the config.
- **`/ws/workflow`**: per-step progress — `step_start`, `step_done` (with results), `done`.

### 13 MCP tools (3 new workspace tools added in v10)

Full list: analyze, consensus, committee, debate, fetch, sentiment, list_personas, configure, create_persona, workflow, **workspace_get, workspace_set, workspace_profiles**.

### 19 Hermes Skills + augur-terminal meta-skill

Each master has its own Hermes skill. Chinese masters respond in Chinese. New: `augur-terminal` meta-skill as a unified entry point for the full Bloomberg-style terminal (all 13 tools, 15 pages, 4 presets). New: `committee.yaml` Hermes agent for the Committee Chair role.

### Dashboard improvements

- 4-language i18n (zh/en/ja/ko), keyboard shortcuts panel (`?`), PWA installable
- History 52-week heatmap (GitHub style), Optimizer efficient frontier
- CSV export on all main pages, WebSocket-driven Ticker Tape

### Consensus engine

Industry-matrix weights, regime routing (hysteresis + confirmation), point-in-time fundamentals (no look-ahead), MetaModel blending, probability calibration, rolling IC.

### Test coverage

2136 tests passing.

---

## v10.16.9 — OOS Validation (internal, included in v10.0.0)

## What this update fixes

v10.16.8 resolved whether regime detection (bull/bear/sideways crossed with high/low volatility) could flip-flop from a single noisy day. It explicitly left the second half of that gate open: "whether the hand-picked `_REGIME_ADJUSTMENTS` multipliers themselves actually help has never been validated — left for a later P2-4."

This release (v10.16.9) is that validation: in a bear, high-vol market the system boosts Howard Marks's weight and dials down certain growth-style agents' weights. Do those hand-picked numbers, run against real historical data, actually make the consensus's predictions better?

**A more basic problem turned up first.** Before any validation could run, it became clear that historical backtest replay had never fed any day real fundamentals data (PE, PB, ROE, etc.) — those fields stayed at 0 for every single historical day. Value-style agents like Marks and Graham score primarily off those fundamentals. Feeding them a constant 0 pins their score to a constant — and a constant score's rank never moves no matter how it's reweighted. In other words, before this fix, "does regime weighting help" was not a question the system could actually answer — testing it would have looked like testing something, while testing nothing.

This release first adds real, look-ahead-safe historical fundamentals data (see "point-in-time fundamentals" below), then runs the actual validation on top of it.

## What the validation found

**Result: across 37 stocks and roughly 4.4 years of out-of-sample data, the regime-weighted consensus showed no clear, consistent improvement over a flat equal-weight consensus — the size and direction of the effect was small and inconsistent across all five regime buckets.**

This is not a claim that the hand-picked weights are "wrong," nor that they're "validated" — it's the first time this was honestly measured, and the honest result is a wash. Whether to keep, retune, or drop these multipliers is a product decision left for later; this release doesn't make that call.

A per-agent cross-sectional IC breakdown gives a finer directional read: in those 9 bear-high-vol days, Benjamin Graham's cross-sectional IC was +0.086 (consistent with the hypothesis that Graham's value framework works in bear markets), while Howard Marks was −0.030 (counter to the hypothesis for these specific 9 days). This is not a general claim about either agent — it's what happened in those two specific market episodes. The statistically meaningful bucket is SIDEWAYS (n=746), where the delta between regime-weighted and flat consensus is +0.0009, essentially zero.

One caveat worth calling out specifically: the bear-market, high-volatility bucket has very few qualifying days — across the 37-stock universe, only 9 trading days had at least 5 stocks with real point-in-time fundamentals available on a day classified as bear-high-vol — and those 9 days aren't spread out; they cluster into two short historical episodes (the August 2024 yen-carry-unwind selloff, and the April 2025 tariff-shock selloff). A confidence interval computed on a sample like that is a mechanical number, not statistically meaningful evidence — it can only be read as "directionally, this is what happened in those two specific weeks," not generalized into a claim about bear markets overall. The 2022 bear market is not covered at all — FY2022 annual filings only become available (with the 90-day lag) around late March 2023, after the bear market had ended.

## What's fixed (two bugs found along the way)

- **Point-in-time fundamentals**: added a new fundamentals lookup specifically for historical backtest replay — given a stock and a historical date, it returns only the financial-statement data that would actually have been publicly available as of that date (annual filings are conservatively assumed to need 90 days after fiscal year-end before they're "available," since real per-filing dates aren't accessible in this environment). If no filing is yet available for a given date, that day is dropped outright rather than silently filled with zeros.
- **Bug 1: Yahoo Finance's oldest retained annual data column is sometimes entirely empty, but this used to be mistaken for real data.** Once an annual statement column ages out of Yahoo Finance's full retention window, every value in that column goes blank (NaN) — but the column's date label is still there. The old logic only checked whether that date label passed the 90-day lag rule, not whether the column actually contained any real numbers — so for some historical dates, the system would "successfully" return a complete set of all-zero fundamentals instead of correctly flagging the day as having insufficient data. This is exactly the same problem described above in a different guise: the whole point was to avoid look-ahead and avoid faking zeros, and this specific edge case slipped past both protections. Fixed by requiring at least one core financial figure to be a real, non-blank number before treating a period as "available."
- **Bug 2: Yahoo Finance's API itself occasionally returns an empty result for no good reason, and the old logic would permanently remember that empty result as the truth.** Direct testing showed that three back-to-back, fresh-process requests for the same stock's data returned valid numbers twice and a completely empty result once — i.e., this is a real, occasional flakiness on Yahoo Finance's end, not a bug in how the request was made. But the old design fetched each stock's statements exactly once per run and cached whatever came back, permanently. If that one fetch happened to land on the empty response, that stock would be wrongly treated as having no financial data for the rest of that run. Fixed by retrying a few times before accepting and permanently caching an empty result as genuine.

## Test status

- New: `tests/test_pit_fundamentals.py`, 16 tests, all offline/deterministic (no network), all passing.
- Full suite: **2104 tests passing**, 0 failures (run both before and after this work to confirm no regressions).

## What this release does NOT conclude

- It does not render a final verdict on whether regime weighting should be kept, changed, or removed — that's a product decision; this release's job was only to deliver the data and the validation honestly.
- The bear-market, high-volatility result specifically is backed by limited evidence (two short historical episodes, 9 trading days) and should be read as a directional observation about those two periods, not a general statement about how bear markets should be weighted.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
