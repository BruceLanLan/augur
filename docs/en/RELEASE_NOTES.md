# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

---

## v14.1.0 — A real ETF consensus, no placeholder 5.0, true-range ATR (2026-11-26)

v14.0 stopped scoring ETFs as companies, but only Dalio applied, so ETFs never got a consensus. This release fills that gap and removes a few misleading numbers.

### ETFs get a real consensus

- Marks, Soros and ARPS gained a fund reading that uses only technical, market and ETF-profile data (price vs. the 50/200-day averages, the 52-week range, RSI, MACD, 20-day volatility), never company financials. With Dalio, 4 of the 18 masters now apply to funds.
- With at least 3 applicable masters an ETF gets a result labelled "Fund consensus": equal weights scaled by data coverage, without the industry weights, learned weights or news-sentiment shift tuned for stocks; no position size, and nothing written to the learning records. Live SPY on 2026-11-26: NEUTRAL, 5.0/10, 43% confidence, 4 of 18 masters.
- When technicals are missing (for example only a manual price), these masters abstain with "fund technicals missing" and the ETF is still WITHHELD. The output lists "rules not applicable to funds" and "fund technicals missing" separately.
- Because ETFs now have a real consensus, watchlist monitoring (`augur watchlist watch`), the dashboard watchlist and `augur cron` alerts can fire on them; a withheld consensus never alerts.

### A withheld consensus never shows as 5.0

In v14.0 a fund without a consensus still showed as "HOLD 5.0" in many places. It now reads WITHHELD or `--` everywhere: dashboard history, signals, watchlist, portfolio, scanner, home page and stock-page trend chart, `augur cron` summaries, the Telegram / Slack / Lark / WeChat bots, built-in skills and the dossier, and the MCP debate tool. The `augur cron` case was a real bug: the 5.0 placeholder cleared the default threshold of 3, so it alerted on funds with no conclusion; `augur watchlist watch --alert-above / --alert-below` had the same problem and is fixed too. Also fixed: the committee page said "0 masters" when none were selected, and CLI tables lost alignment with emoji and CJK text.

### Indicators and backtests closer to reality

- **ATR uses the true range** (daily highs and lows, Wilder smoothing). True ATR is about 1.86x the old approximation, so the Munger and Dalio volatility thresholds were recalibrated on 41 tickers and 10,373 windows (Munger > 3% → > 5.75%, Dalio < 2 / > 5 → < 3.75 / > 9.25), keeping overall trigger rates where they were. **Dalio and Munger scores change for individual tickers**; most visibly, Munger's high-volatility rule now almost never fires on US large caps, HK and A-shares. See the [ATR recalibration note](../research/ATR_RECALIBRATION_2026-11.md) (Chinese).
- **Backtests** now give replayed days the same technical fields as production (before only RSI and MACD, so "MACD above signal" became "MACD above 0" and "price above the average" was always true), over a 63-bar window with a warm-up; missing forward returns are skipped instead of counted as 0. **Backtest and regime-IC numbers therefore differ from earlier versions**, as expected.
- **Learning entry price**: a prediction made after the close (HK 16:00, A-shares 15:00, otherwise New York 16:00) enters at the next session's close instead of a close it had already seen.
- Live SPY's dividend yield read as 100% (yfinance changed the field's unit); no master reads that field, so scores are unaffected.

### When upgrading

- Scripts that parse ETF output: ETFs usually have a signal and score now; don't assume WITHHELD.
- If you compare backtest numbers across versions, re-run your baseline after upgrading.
- Full list: "Upgrading from v14.0 to v14.1" in the README and [CHANGELOG.md](../../CHANGELOG.md).

### Not done yet

Backtest contexts still lack the 52-week position and the 200-day average; compact history records from before v14.1 still store a withheld fund consensus as 5.0; whether 20-day volatility should use sample variance is undecided; persona text is Chinese only; VIX and regime features do not reach persona contexts; funds have no daily change percentage. All listed in the [ROADMAP](../ROADMAP.md) (Chinese).

---

## v14.0.0 — ETF-native analysis, correctness fixes, a clear LLM role (2026-11-26)

This release answers two things: a user asked "can it analyse ETFs?" and "does Augur actually use an LLM?" (Issue #5), and another user pointed out that the RSI formula was wrong (PR #10). Three threads.

### Thread one: ETFs are no longer scored as companies

Before, entering SPY made the 18 masters apply company-financials rules to a fund, which produced conclusions like "small cap" or "gross margin too low". Now `augur fetch / consensus / analyze / report` first recognise an ETF (by yfinance's instrument type for US and HK funds, by code prefix for A-shares) and show an ETF overview: AUM (in USD), expense ratio, yield, NAV and its date, premium/discount, top-10 holdings weight, bid/ask spread and look-through P/E, followed by a health checklist (high expense ratio, AUM small enough to risk closure, premium/discount above 1%, concentrated holdings, wide spread).

The premium/discount always compares against the close on the NAV date. US and HK NAVs come without a date, so it is inferred as the session before the latest bar and marked as inferred; A-share ETF NAVs and their real dates come from Sina's public quote endpoint.

Masters whose rules are built on company financials explicitly **abstain** on a fund and say why. In this release only Dalio's rules apply to funds (decided by a test: change company fields on an ETF and see whose score moves). With fewer than 3 applicable masters there is no consensus: the output says WITHHELD, gives no position size and writes nothing to the learning records. The dashboard stock page has a new ETF card.

### Thread two: calculation errors that biased scores

- **RSI**: it looked only at the last 14 changes (Cutler's RSI); it now uses Wilder smoothing, the industry standard, matching TA-Lib. The seven masters that read RSI score differently. The two tests from PR #10 are in the suite as written, and the fix adds no dependency.
- **Non-USD stocks**: HK and A-share market caps and free cash flow were used as if they were USD, so Tencent looked like a $3 trillion company. Amounts are now converted at the FX rate; Tencent is about $397.5B. Without a rate nothing is converted and the output names the local currency.
- **Dayu's volatility rule** had a unit bug and never fired, so every stock got the "low volatility, size up" bonus; now higher volatility costs more points.
- Also: Thiel counts Google, Meta and Tencent as tech; a neutral verdict sizes the position at 0; `--json` prints pure JSON that scripts can parse directly; the fear/greed gauge is recalibrated (VIX 28 reads as Fear); the backtest page no longer "derives" drawdown and Sharpe from the hit rate.

### Thread three: what Augur does and doesn't do with LLMs

Augur's scoring **does not call any LLM**. It is deterministic rules, so the same inputs give the same scores, which is what makes backtesting possible. LLMs come in two places: through MCP, where an agent such as Claude Code calls Augur and interprets the scores and evidence with its own model (`claude mcp add augur -- augur-mcp`); and the optional persona chat, using an OpenAI-compatible key you configure. The README has a new section, "How Augur uses LLMs". Clean-up: the MCP tool `augur_configure` wrote a setting nothing ever read and is now deprecated; the `[llm]` extra no longer installs the unused `anthropic` package.

### When upgrading

- Scripts that read progress text from stdout with `--json` must read stderr instead.
- Code that reads `MarketContext`: amounts for non-USD instruments are now USD.
- The full list is in the README section "Upgrading from v13 to v14" and in [CHANGELOG.md](../../CHANGELOG.md).

### Not done yet

ATR with true range, ETF premium/discount history and tracking error, more master rules that apply to funds, and a clean-up of ETF learning records written before v14 are listed as v14 deferred items in the [ROADMAP](../ROADMAP.md) (Chinese).

---

## v10.15.0 — Public sync release (2026-07-15)

The last public release was v10.0.0 on 2026-06-29 (Terminal Workspace + 13 MCP tools). This release brings over three and a half weeks of development since then -- it's a lot, organized into four threads.

### Thread one: fundamentals are now real (SEC EDGAR)

The PE, ROE, gross margin, etc. the 18 masters see used to be simplified calculations from yfinance, with historical depth only back to roughly 2022. They now come from the SEC EDGAR system's official filings (real numbers from 10-K/10-Q reports), with historical depth back to roughly 2011 depending on the company (US tickers and US-listed Chinese ADRs only). The same data pull also unlocked two new signals: **insider buying signal** (tracks executives'/directors' real trailing-90-day open-market trades) and **institutional flow signal** (tracks quarterly position changes at Berkshire Hathaway, Renaissance Technologies, Bridgewater, and others). Also new: `augur guidance TICKER` (opt-in, off by default), which uses an LLM to extract management outlook sentiment from the latest filing.

### Thread two: three places that looked like they were working but weren't

- Consensus scores used to be diluted by half through a never-validated stub model -- now off by default.
- The Dashboard's "backtest" page used to default to synthetic, program-generated data -- now defaults to real historical data; synthetic data is still available but requires an explicit opt-in and is clearly labeled.
- The system had always advertised "the masters get more accurate with use," but the learning engine never actually accumulated data -- predictions now persist immediately, with a scheduled job auto-resolving due predictions. Also quietly retired two mechanisms that had no real validation behind them: the always-fake X (Twitter) sentiment weight, and the hand-picked regime-weight multipliers, which real-data validation found didn't help.

### Thread three: new tools

- **`augur doctor [--offline]`**: a one-shot local environment diagnostic -- checks the Python/SSL toolchain for known bad combinations that break yfinance, optional API key configuration, live data-source connectivity, and learning-engine data accumulation progress. Every run also records a connectivity data point locally (`~/.augur/provider_stats.json`), building a 7-day trend so a dead data source surfaces early (this release's own sync run is what caught and documented stooq's dead endpoints, for instance).
- **Weekly real-network data-source smoke test**: a new scheduled GitHub Actions job that runs real connectivity checks automatically.
- **Two new research scripts**: `scripts/factor_attribution.py` (computes real predictive power for each of ~90 named investment factors individually, with a built-in multiple-comparison guard) and `scripts/generate_rolling_ic.py` (fills in the generator script the consensus engine's "dynamically reweight by recent performance" logic had always been missing). The first full real-data runs of both scripts turned up an honest finding: the historical backtest-replay pipeline has never had real historical data for "insider ownership %" or "institutional ownership %," which silently degrades some masters' related judgments in any historical validation -- not a new problem introduced by this release, but the first time it's been systematically found and documented, and there's currently no free data source to fix it with. See `docs/FACTOR_ATTRIBUTION_FINDINGS_2026-07.md` for the full writeup.

### Thread four: engineering health

`cli.py` (1476 lines) and the old `dashboard/` God file (4338 lines) have both been split into focused modules; a real packaging bug -- `pip install` producing a package missing the entire dashboard directory -- was found and fixed with a regression test. Right before this sync, an additional real bug was found and fixed: an avatar-image path miscalculated by one directory level during that refactor, 404-ing every persona avatar site-wide -- no existing test caught it; it only surfaced from actually opening the app in a real browser.

### Test coverage

2461 tests passing (2136 at the time of the v10.0.0 release).

---

## v10.14.0 — rolling_ic.json generator (2026-07-14)

The consensus engine has always had a "dynamically reweight masters by
recent performance" blend, but there was never actually a script that
generated the data file it reads -- so that logic has been silently
no-opping since it shipped, the exact same situation as the diversity-
penalty feature before its own fix (code waiting on a file nobody ever
generated). This release adds that generator: it computes each master's
real "how accurate were recent predictions" score from historical data and
writes it as a weights file. Whether these weights actually improve
consensus quality hasn't been validated with a before/after comparison yet
-- writing the file just stops the logic from being inert, it doesn't by
itself prove the blend helps.

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
