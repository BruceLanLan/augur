# -*- coding: utf-8 -*-
"""B3: does regime weighting help in a genuinely different bear-market
episode (the 2020 COVID crash) from the one the original disable decision
was based on?

Background
----------
``_REGIME_ADJUSTMENTS`` in ``src/augur/consensus/regime_weights.py`` was
disabled to all-empty dicts in commit ``a4e7597`` (v10.6.0) after
``regime_weight_oos.py``'s real OOS validation over 2022-01..2026-06 found
no clear rank-IC benefit. But that window's own honest-summary caveat
already flagged the specific reason BEAR_HIGH_VOL coverage was thin there:
FY2022 annual filings aren't as-of-available until ~March 2023 (90-day
filing-lag guard), by which point the 2022 bear market had already ended.
The roadmap doc left one concrete follow-up: push the window back to
2018-2020, where FY2019 filings (typically available Jan-Feb 2020 for
large accelerated filers) might actually land *before* the COVID crash
(Feb-Apr 2020) -- this script is that follow-up, not attempted until now.

Method
------
Same machinery as ``regime_weight_oos.py`` (``compute_cross_sectional_regime_ic``,
the same 37-ticker universe from ``scripts/_replay_universe.py``), but:

  1. A 2018-01-01..2020-12-31 window instead of the shared 2022-2026 one,
     to actually cover the COVID crash.
  2. The ORIGINAL hand-picked multipliers (the exact values from commit
     ``a4e7597~1``, before they were zeroed out) are restored in this
     process's memory only, via monkeypatching
     ``augur.consensus.regime_weights._REGIME_ADJUSTMENTS`` -- never
     written to disk, never re-enabled in the shipped module. Testing
     against today's all-empty dict would trivially show delta=0
     everywhere (flat vs. itself), which answers nothing.

This is NOT part of the pytest suite (real network calls, reports numbers
rather than pass/fail) -- same convention as every other script in this
family. Run manually:

    .venv/bin/python scripts/regime_weight_oos_2018_2020.py

Honest scope note (read before interpreting any number this prints)
---------------------------------------------------------------------
Same statistical caveats as ``regime_weight_oos.py`` apply: BEAR_HIGH_VOL
days cluster into episodes, not independent samples; a bootstrap CI on a
handful of clustered days is directional evidence about specific historical
weeks, not a general statistical claim. Whether EDGAR's 2018-2020 coverage
is actually as good as the 2022+ window is itself an open question this
script answers empirically (see the per-ticker record counts it prints) --
do not assume it before seeing the real numbers.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from augur.backtest import (  # noqa: E402
    build_date_to_regime,
    fetch_ticker_replay_records,
    compute_cross_sectional_regime_ic,
)
from augur.consensus import regime_weights as _regime_weights_module  # noqa: E402
from _replay_universe import UNIVERSE  # noqa: E402

START = "2018-01-01"
END = "2020-12-31"

# The exact original multipliers from commit a4e7597~1 (immediately before
# Phase D's disable commit), restored here in-memory only for this OOS
# re-test -- not retyped from memory, copy-verified against `git show
# a4e7597~1:src/augur/consensus/regime_weights.py`.
_ORIGINAL_REGIME_ADJUSTMENTS = {
    "BULL_LOW_VOL": {
        "lynch": 1.22, "cathie_wood": 1.18, "aschenbrenner": 1.12, "thiel": 1.08,
        "marks": 0.88, "graham": 0.9,
    },
    "BULL_HIGH_VOL": {
        "marks": 1.22, "dalio": 1.18, "graham": 1.12, "munger": 1.08,
        "cathie_wood": 0.85, "aschenbrenner": 0.88, "soros": 1.05,
    },
    "BEAR_LOW_VOL": {
        "graham": 1.28, "buffett": 1.22, "marks": 1.18, "munger": 1.12,
        "cathie_wood": 0.75, "aschenbrenner": 0.78, "thiel": 0.82,
    },
    "BEAR_HIGH_VOL": {
        "marks": 1.32, "dalio": 1.28, "soros": 1.18, "graham": 1.15, "buffett": 1.1,
        "cathie_wood": 0.72, "aschenbrenner": 0.75,
    },
    "SIDEWAYS": {
        "munger": 1.12, "fisher": 1.12, "marks": 1.08, "buffett": 1.05, "lynch": 1.05,
    },
}


def main() -> None:
    print("*** Restoring original (pre-v10.6.0-disable) regime multipliers "
          "in-memory for this OOS re-test only -- not written to disk. ***")
    _regime_weights_module._REGIME_ADJUSTMENTS = _ORIGINAL_REGIME_ADJUSTMENTS

    print(f"\nUniverse: {len(UNIVERSE)} tickers")
    print(f"Window: {START} .. {END}  (2018-2020, testing whether FY2019 filings")
    print("landed before the COVID crash the way the roadmap doc speculated)")

    print("\nBuilding date_to_regime (one VIX+SPY pull for the whole window)...")
    date_to_regime = build_date_to_regime(START, END)
    regime_counts = Counter(date_to_regime.values())
    print(f"  regime distribution across all trading days: {dict(regime_counts)}")
    bhv_dates = sorted(d for d, r in date_to_regime.items() if r == "BEAR_HIGH_VOL")
    if bhv_dates:
        print(f"  BEAR_HIGH_VOL raw dates: {len(bhv_dates)}, "
              f"range {bhv_dates[0]} .. {bhv_dates[-1]}")

    print(f"\nFetching point-in-time replay records for {len(UNIVERSE)} tickers "
          f"over 2018-2020 (first real run of this window -- EDGAR cache is cold "
          f"for these dates, can take a while)...")
    records_by_ticker = {}
    for ticker in UNIVERSE:
        # fetch_ticker_replay_records's period defaults to "5y" -- a
        # yfinance lookback from TODAY, not from END. Since today is well
        # past 2020, the default silently returns zero price history for
        # this window (confirmed: a first run with the default returned 0
        # records for all 37 tickers). "max" is required to actually reach
        # back to 2018.
        recs = fetch_ticker_replay_records(ticker, START, END, period="max")
        records_by_ticker[ticker] = recs
        print(f"  {ticker}: {len(recs)} records")

    total_records = sum(len(v) for v in records_by_ticker.values())
    zero_record_tickers = [t for t, v in records_by_ticker.items() if not v]
    print(f"\nTotal records across universe: {total_records}")
    if zero_record_tickers:
        print(f"  WARNING -- tickers with ZERO records (network hiccup or "
              f"genuinely no 2018-2020 PIT coverage, re-run to check): {zero_record_tickers}")

    print("\nComputing cross-sectional regime IC (flat equal-weight vs "
          "ORIGINAL regime-weighted consensus, restored in-memory)...")
    result = compute_cross_sectional_regime_ic(records_by_ticker, date_to_regime)

    print(f"\nTotal qualifying days (>= 5 tickers with PIT data): "
          f"{result['n_days_total']}")
    print(f"Days skipped as too thin (< 5 tickers with PIT data): "
          f"{result['n_days_skipped_thin']}")

    print("\n=== Per-regime IC: flat vs regime-weighted (ORIGINAL multipliers) ===")
    print(f"{'regime':<16}{'n_days':>8}{'flat_ic':>12}{'regime_ic':>12}{'delta':>12}")
    for regime, stats in sorted(result["per_regime"].items(), key=lambda kv: -kv[1]["n_days"]):
        print(f"{regime:<16}{stats['n_days']:>8}{stats['flat_ic_mean']:>12.4f}"
              f"{stats['regime_ic_mean']:>12.4f}{stats['delta_mean']:>12.4f}")

    print("\n=== BEAR_HIGH_VOL block-bootstrap CI (delta = regime_ic - flat_ic) ===")
    bear_bootstrap = result.get("bear_high_vol_bootstrap")
    if bear_bootstrap is None:
        print("  No BEAR_HIGH_VOL days with sufficient PIT coverage in this "
              "window/universe -- cannot compute. (This alone would answer the "
              "roadmap's open question: EDGAR's 2018-2020 coverage doesn't clear "
              "the bar either, for the same or a different reason than 2022.)")
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
        "This script re-tests the ORIGINAL (pre-v10.6.0-disable) regime\n"
        "multipliers against the 2018-2020 window, using real point-in-time\n"
        "EDGAR fundamentals (no look-ahead; days without as-of-available\n"
        "fundamentals are dropped, never zero-filled). The multipliers remain\n"
        "disabled in the shipped code regardless of this result -- re-enabling\n"
        "them, if this result supported it, would be a separate decision.\n"
        "\n"
        "SIDEWAYS and the *_LOW_VOL buckets have the most days and are the\n"
        "statistically meaningful part of this output. BEAR_HIGH_VOL numbers,\n"
        "even if the CI excludes zero, are directional evidence about\n"
        "whichever specific 2020 weeks got covered -- not a general statistical\n"
        "claim about bear-market regime weighting."
    )


if __name__ == "__main__":
    main()
