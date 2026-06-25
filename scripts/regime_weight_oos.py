# -*- coding: utf-8 -*-
"""P2-4 out-of-sample validation: do the hand-picked ``_REGIME_ADJUSTMENTS``
multipliers in ``src/augur/consensus/regime_weights.py`` actually improve
cross-sectional rank prediction quality vs. a flat equal-weight consensus?

This is NOT part of the pytest suite (it makes many live network calls to
yfinance over a 30-50 ticker, multi-year universe and reports numbers rather
than asserting pass/fail). Run it manually:

    .venv/bin/python scripts/regime_weight_oos.py

Background
----------
Before this script, ``Backtester.run_live_backtest`` never populated real
fundamentals during historical replay -- pe/pb/roe stayed at the
``MarketContext`` dataclass default of 0 for every single day. Any prior
"validation" of ``_REGIME_ADJUSTMENTS`` against that path was null by
construction: reweighting a constant-zero value-agent score cannot move a
rank-IC no matter what the multiplier is.

This script uses the point-in-time fundamentals provider
(``augur.consensus.pit_fundamentals.fetch_pit_fundamentals``) to give every
historical day real, as-of-available fundamentals (or correctly drop the day
as "insufficient" -- never zero-filled), then asks the only question that is
actually testable: on a single day, across many tickers, does ranking by the
regime-weighted consensus correlate better with subsequent 20-day returns
than ranking by a flat equal-weight consensus? (See
``augur.backtest.compute_cross_sectional_regime_ic`` for why this must be a
CROSS-SECTIONAL per-day comparison, not a per-ticker time series: annual
fundamentals update once a year per ticker, so a per-ticker time series of
value-agent scores is a near-constant step function for most of the year.)

Honest scope and known limitations (read before interpreting any number
this script prints)
------------------------------------------------------------------------
1. BEAR_HIGH_VOL coverage is thin and clustered, not evenly spread. Regime
   is a market-wide label (computed once from VIX+SPY), not a per-ticker
   one -- a wider ticker universe adds cross-sectional breadth *within* a
   day, it does NOT create more BEAR_HIGH_VOL days. Calendar-year 2022
   itself contributes ~zero usable BEAR_HIGH_VOL days for most tickers in
   this universe, because FY2022 annual filings are not as-of-available
   (90-day filing-lag guard) until roughly late March 2023 -- i.e. after
   the 2022 bear market had already ended. The BEAR_HIGH_VOL days with real
   PIT fundamentals were concentrated in two short, adjacent-day market
   episodes: 2024-08 (yen-carry-unwind selloff) and 2025-04 (tariff-shock
   selloff). The exact count depends on how many tickers yfinance returns
   real data for on each date; see the script output for the actual n_days.
2. Because of (1), the BEAR_HIGH_VOL bootstrap CI is a mechanical
   computation over ~2 autocorrelated episodes, not an independent-sample
   estimate. A CI that excludes zero on n<30 days clustered into 1-2
   episodes is NOT statistical evidence that the regime weights "work" in
   bear markets -- it is, at best, a directional read on two specific
   historical weeks. The script prints an explicit low-power warning
   whenever this applies; do not strip it out of any downstream report.
3. yfinance itself has been observed to be flakey: a `.financials` fetch
   for the same ticker, in fresh processes, has returned valid data twice
   and an empty DataFrame once. ``pit_fundamentals.py`` now retries a few
   times before accepting an empty result and caching it, and the day's
   look-ahead guard separately rejects yfinance's NaN-padded oldest annual
   column as "available" -- but a residual amount of network nondeterminism
   (timeouts, rate limiting) across a 30-50 ticker multi-year run is still
   possible and would show up as fewer-than-expected records for some
   tickers. Re-running this script and comparing record counts per ticker
   is the cheapest way to spot that if results look surprising.
4. SIDEWAYS and the *_LOW_VOL buckets have far more days and are the more
   statistically meaningful part of this output -- not BEAR_HIGH_VOL.
"""

from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, "src")

from augur.backtest import (  # noqa: E402
    build_date_to_regime,
    fetch_ticker_replay_records,
    compute_cross_sectional_regime_ic,
)

# 38 tickers, cross-sector: mega-cap tech, banks, energy, consumer staples,
# healthcare, industrials. Deliberately not curated to favor any agent style.
UNIVERSE = [
    # Tech / growth
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AMD", "CRM", "ORCL", "ADBE",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP",
    # Energy
    "XOM", "CVX", "COP", "SLB",
    # Consumer staples / retail
    "KO", "PG", "WMT", "COST", "MCD", "PEP",
    # Healthcare
    "JNJ", "PFE", "UNH", "MRK", "ABBV", "LLY",
    # Industrials
    "CAT", "BA", "HON", "GE",
]

START = "2022-01-01"
END = "2026-06-01"


def main() -> None:
    print(f"Universe: {len(UNIVERSE)} tickers")
    print(f"Window: {START} .. {END}")

    print("\nBuilding date_to_regime (one VIX+SPY pull for the whole window)...")
    date_to_regime = build_date_to_regime(START, END)
    regime_counts = Counter(date_to_regime.values())
    print(f"  regime distribution across all trading days: {dict(regime_counts)}")
    bhv_dates = sorted(d for d, r in date_to_regime.items() if r == "BEAR_HIGH_VOL")
    if bhv_dates:
        print(f"  BEAR_HIGH_VOL raw dates: {len(bhv_dates)}, "
              f"range {bhv_dates[0]} .. {bhv_dates[-1]}")

    print(f"\nFetching point-in-time replay records for {len(UNIVERSE)} tickers "
          f"(this makes one fetch_history + as-of fundamentals lookups per "
          f"ticker; can take a while)...")
    records_by_ticker = {}
    for ticker in UNIVERSE:
        recs = fetch_ticker_replay_records(ticker, START, END)
        records_by_ticker[ticker] = recs
        print(f"  {ticker}: {len(recs)} records")

    total_records = sum(len(v) for v in records_by_ticker.values())
    zero_record_tickers = [t for t, v in records_by_ticker.items() if not v]
    print(f"\nTotal records across universe: {total_records}")
    if zero_record_tickers:
        print(f"  WARNING -- tickers with ZERO records (network hiccup or "
              f"genuinely no PIT coverage, re-run to check): {zero_record_tickers}")

    print("\nComputing cross-sectional regime IC (flat equal-weight vs "
          "apply_regime_weights-based regime-weighted consensus)...")
    result = compute_cross_sectional_regime_ic(records_by_ticker, date_to_regime)

    print(f"\nTotal qualifying days (>= 5 tickers with PIT data): "
          f"{result['n_days_total']}")
    print(f"Days skipped as too thin (< 5 tickers with PIT data): "
          f"{result['n_days_skipped_thin']}")

    print("\n=== Per-regime IC: flat vs regime-weighted ===")
    print(f"{'regime':<16}{'n_days':>8}{'flat_ic':>12}{'regime_ic':>12}{'delta':>12}")
    for regime, stats in sorted(result["per_regime"].items(), key=lambda kv: -kv[1]["n_days"]):
        print(f"{regime:<16}{stats['n_days']:>8}{stats['flat_ic_mean']:>12.4f}"
              f"{stats['regime_ic_mean']:>12.4f}{stats['delta_mean']:>12.4f}")

    print("\n=== Per-agent cross-sectional IC, by regime (diagnostic) ===")
    print("    (+ means agent's ticker ranking predicted returns; - means anti-predictive)")
    for regime, agent_ics in result["per_agent_by_regime"].items():
        n_days = result["per_regime"].get(regime, {}).get("n_days", 0)
        print(f"\n  {regime} (n_days={n_days}):")
        for aid, v in sorted(agent_ics.items(), key=lambda kv: -kv[1]):
            print(f"    {aid:<16}{v:>8.3f}")

    print("\n=== BEAR_HIGH_VOL block-bootstrap CI (delta = regime_ic - flat_ic) ===")
    bear_bootstrap = result.get("bear_high_vol_bootstrap")
    if bear_bootstrap is None:
        print("  No BEAR_HIGH_VOL days with sufficient PIT coverage in this "
              "window/universe -- cannot compute.")
    else:
        print(f"  n_days={bear_bootstrap['n_days']}  "
              f"delta_mean={bear_bootstrap['delta_mean']}  "
              f"CI=[{bear_bootstrap['ci_low']}, {bear_bootstrap['ci_high']}]  "
              f"(block_size={bear_bootstrap['block_size']}, "
              f"n_blocks_per_resample={bear_bootstrap['n_blocks_per_resample']})")
        if bear_bootstrap.get("low_power_warning"):
            print(f"\n  *** {bear_bootstrap['low_power_warning']} ***")

    print(
        "\n"
        "=== Honest summary (read this before drawing any conclusion) ===\n"
        "This script measures whether apply_regime_weights' hand-picked\n"
        "_REGIME_ADJUSTMENTS multipliers improve cross-sectional rank-IC vs a\n"
        "flat equal-weight consensus, bucketed by regime, using real\n"
        "point-in-time fundamentals (no look-ahead, days without as-of-available\n"
        "fundamentals are dropped, never zero-filled).\n"
        "\n"
        "This script intentionally prints raw numbers and does NOT emit a\n"
        "pass/fail verdict. SIDEWAYS and the *_LOW_VOL buckets have the most\n"
        "days and are the statistically meaningful part of this output.\n"
        "BEAR_HIGH_VOL, specifically, is backed by very few days that cluster\n"
        "into 1-2 short market episodes rather than independent observations --\n"
        "treat any BEAR_HIGH_VOL number as directional evidence about those\n"
        "specific historical weeks, not as a general statistical claim about\n"
        "bear-market regime weighting."
    )


if __name__ == "__main__":
    main()
