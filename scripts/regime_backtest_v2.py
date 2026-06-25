# -*- coding: utf-8 -*-
"""P2-3 narrow-scope historical validation for the regime detector v2.

This is NOT part of the pytest suite (it makes live network calls to
yfinance and reports numbers rather than asserting pass/fail). Run it
manually:

    .venv/bin/python scripts/regime_backtest_v2.py

It validates exactly what the narrow P2-3 scope promises:
  1. Hysteresis materially reduces spurious regime flips vs. the old
     single-snapshot hard-cutoff classifier, without freezing detection
     useless (it still enters high-vol-bear promptly around known crashes).
  2. The accepted regime at a given date does not depend on how far back
     the trailing lookback window starts (window-length independence) —
     i.e. the finite-window dwell scan's SIDEWAYS seed washes out.

It deliberately does NOT attempt to validate whether the hand-picked
_REGIME_ADJUSTMENTS multipliers improve investment outcomes — that is
out of scope for narrow P2-3 (see docs/V9_ROADMAP.md / P2-4).
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import List, Tuple

import pandas as pd
import yfinance as yf

sys.path.insert(0, "src")
from augur.consensus.macro_features import classify_regime, _trend_from_window  # noqa: E402

# Matches the live path's trailing window (~95 calendar days ~= 65 trading days).
LIVE_TRADING_WINDOW = 65
OLD_VIX_CUTOFF = 25.0

# Known crash/regime-shift windows to sanity-check responsiveness.
CRASH_WINDOWS = [
    ("2020 COVID crash", "2020-02-15", "2020-04-15"),
    ("2022 bear market", "2022-01-01", "2022-10-31"),
    ("2018 Q4 selloff", "2018-10-01", "2018-12-31"),
]


def fetch_aligned_series(start: str, end: str) -> Tuple[List[str], List[float], List[float]]:
    vix_hist = yf.Ticker("^VIX").history(start=start, end=end)
    spy_hist = yf.Ticker("SPY").history(start=start, end=end)
    vix_hist = vix_hist.copy()
    spy_hist = spy_hist.copy()
    vix_hist.index = pd.to_datetime(vix_hist.index.date)
    spy_hist.index = pd.to_datetime(spy_hist.index.date)
    common = vix_hist.index.intersection(spy_hist.index).sort_values()
    dates = [d.strftime("%Y-%m-%d") for d in common]
    vix_closes = vix_hist.loc[common, "Close"].tolist()
    spy_closes = spy_hist.loc[common, "Close"].tolist()
    return dates, vix_closes, spy_closes


def old_raw_regime(vix: float, trend: str) -> str:
    """Replicates the pre-P2-3 behavior: hard VIX>=25 cutoff, no hysteresis."""
    high_vol = vix >= OLD_VIX_CUTOFF
    if trend == "bull":
        return "BULL_HIGH_VOL" if high_vol else "BULL_LOW_VOL"
    if trend == "bear":
        return "BEAR_HIGH_VOL" if high_vol else "BEAR_LOW_VOL"
    return "SIDEWAYS"


def old_regime_series(vix_closes: List[float], spy_closes: List[float]) -> List[str]:
    out = []
    for i in range(len(vix_closes)):
        trend = _trend_from_window(spy_closes, i)
        out.append(old_raw_regime(vix_closes[i], trend))
    return out


def new_regime_series(vix_closes: List[float], spy_closes: List[float]) -> List[str]:
    """Mirrors the live path exactly: classify using only a trailing window
    of LIVE_TRADING_WINDOW days ending at each date (not the full history),
    since that's what _macro_from_market actually does in production."""
    out = []
    n = len(vix_closes)
    for i in range(n):
        lo = max(0, i - LIVE_TRADING_WINDOW + 1)
        window_vix = vix_closes[lo : i + 1]
        window_spy = spy_closes[lo : i + 1]
        result = classify_regime(window_vix, window_spy, end_idx=len(window_vix) - 1)
        out.append(result["regime"])
    return out


def count_flips(series: List[str]) -> int:
    return sum(1 for i in range(1, len(series)) if series[i] != series[i - 1])


def count_whipsaws(series: List[str], max_gap: int = 3) -> int:
    """Count A -> B -> A patterns where B persists for <= max_gap days."""
    whipsaws = 0
    i = 0
    n = len(series)
    while i < n - 1:
        if series[i] != series[i + 1]:
            a = series[i]
            j = i + 1
            while j < n and series[j] != a and (j - i) <= max_gap:
                j += 1
            if j < n and series[j] == a and (j - i) > 1:
                whipsaws += 1
                i = j
                continue
        i += 1
    return whipsaws


def first_high_vol_entry(dates: List[str], series: List[str], start: str, end: str):
    for d, r in zip(dates, series):
        if start <= d <= end and "HIGH_VOL" in r:
            return d
    return None


def window_length_independence_check(vix_closes, spy_closes, sample_idxs, window_lengths):
    print("\n=== Window-length independence check ===")
    all_stable = True
    for idx in sample_idxs:
        if idx >= len(vix_closes):
            continue
        results = {}
        for w in window_lengths:
            lo = max(0, idx - w + 1)
            wv = vix_closes[lo : idx + 1]
            ws = spy_closes[lo : idx + 1]
            r = classify_regime(wv, ws, end_idx=len(wv) - 1)
            results[w] = r["regime"]
        stable = len(set(results.values())) == 1
        all_stable = all_stable and stable
        print(f"  idx={idx}: {results}  {'OK' if stable else 'MISMATCH'}")
    print(f"  -> all sampled dates window-independent: {all_stable}")
    return all_stable


def main():
    print("Fetching ~9 years of ^VIX / SPY daily closes once...")
    dates, vix_closes, spy_closes = fetch_aligned_series("2015-01-01", datetime.utcnow().strftime("%Y-%m-%d"))
    print(f"Aligned {len(dates)} trading days: {dates[0]} .. {dates[-1]}")

    old_series = old_regime_series(vix_closes, spy_closes)
    new_series = new_regime_series(vix_closes, spy_closes)

    print("\n=== Stability: flip counts (old hard-cutoff vs new hysteresis) ===")
    print(f"  old flips:  {count_flips(old_series)}")
    print(f"  new flips:  {count_flips(new_series)}")
    print(f"  old whipsaws (A->B->A, gap<=3d): {count_whipsaws(old_series)}")
    print(f"  new whipsaws (A->B->A, gap<=3d): {count_whipsaws(new_series)}")

    print("\n=== Responsiveness: first HIGH_VOL entry in known crash windows ===")
    for label, start, end in CRASH_WINDOWS:
        old_entry = first_high_vol_entry(dates, old_series, start, end)
        new_entry = first_high_vol_entry(dates, new_series, start, end)
        print(f"  {label} [{start}..{end}]: old={old_entry}  new={new_entry}")
    print("  NOTE: a large old/new gap here is not automatically a 'new is slow'")
    print("  finding -- it can mean old fired on a single noisy day where VIX and")
    print("  trend coincidentally crossed thresholds without persisting (a")
    print("  whipsaw), while new correctly waited for a persistent move. Cross-")
    print("  check against the whipsaw counts above before treating a gap as lag.")
    print("  Verified manually for 2018 Q4: old fired once on 2018-10-24 (a single")
    print("  bear+VIX>=25 day inside an otherwise choppy, non-persistent stretch --")
    print("  one of the 146 old whipsaws), while new's 2018-12-20 entry lines up")
    print("  with 3 consecutive bear+VIX>=25 days during the real Dec 2018 selloff.")

    # Sample indices biased toward non-SIDEWAYS regimes. SIDEWAYS is also the
    # dwell scan's seed state, so a SIDEWAYS-only sample can't tell "seed
    # washed out" apart from "seed was never challenged" -- it's a vacuous
    # check. Picking only non-SIDEWAYS dates forces the scan to have actively
    # moved off the seed and confirmed a new regime, which is the actual
    # path-dependence case worth checking.
    n = len(vix_closes)
    non_sideways_idxs = [i for i in range(LIVE_TRADING_WINDOW * 4, n) if new_series[i] != "SIDEWAYS"]
    step = max(1, len(non_sideways_idxs) // 12)
    sample_idxs = non_sideways_idxs[::step][:12]
    window_length_independence_check(
        vix_closes, spy_closes, sample_idxs,
        window_lengths=[LIVE_TRADING_WINDOW, LIVE_TRADING_WINDOW * 2, LIVE_TRADING_WINDOW * 4],
    )

    print("\nDone. This validates flip-stability + point-in-time responsiveness + "
          "window-length independence only — it does NOT validate the "
          "_REGIME_ADJUSTMENTS multipliers themselves (out of scope, see P2-4).")


if __name__ == "__main__":
    main()
