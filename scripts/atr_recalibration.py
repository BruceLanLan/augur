#!/usr/bin/env python3
"""Recalibrate persona ATR% thresholds for the v14.1 true-range ATR.

Until v14.0 ``atr`` was the mean of the last 14 ``|C - C[-1]|`` moves; v14.1
uses Wilder's ATR over true ranges when daily highs/lows exist. True range is
never smaller than the close-to-close move, so ATR% reads higher and the
fixed thresholds in munger.py (> 3%) and dalio.py (< 2 / > 5) would fire more
often. This script measures both on real data and proposes thresholds that
keep the pooled trigger rates of the old rule.

Method (mirrors production): for every ticker, fetch ~2y of daily bars with
``yf.Ticker(t).history`` (auto-adjusted, like the provider), slide a 63-bar
window (production fetches ``period="3mo"``) over the last 252 bars, and on
each window compute ATR% = atr / last_close * 100 with the production
function ``augur.data._calculate_technicals_from_prices`` -- closes only
(old path) and closes + highs/lows (new path). New thresholds are the
quantiles of the true-ATR% distribution at the old rule's trigger rates.

It also counts how often switching the 20d realised vol from population to
sample std (ddof=1) moves a window across any persona vol threshold.

Bars are cached as JSON in --cache so re-runs are offline. Network notes:
unset the proxy variables and point AUGUR_DATA_DIR at a temp dir.

Usage:
    env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY \
        PYTHONPATH=src .venv/bin/python scripts/atr_recalibration.py \
        --cache /tmp/atr-cache [--json out.json]
"""

import argparse
import json
import math
import socket
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from augur.data import _calculate_technicals_from_prices  # noqa: E402

UNIVERSE: Dict[str, List[str]] = {
    "us_large": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "XOM",
                 "JNJ", "PG", "KO", "WMT", "TSLA", "AVGO", "UNH"],
    "us_small": ["PLUG", "RIOT", "SOFI", "CROX", "ELF", "AFRM", "UPST", "RKLB",
                 "IONQ", "SMCI"],
    "hk": ["0700.HK", "9988.HK", "0005.HK", "1810.HK", "3690.HK"],
    "cn_a": ["600519.SS", "000858.SZ", "601318.SS", "300750.SZ"],
    "etf": ["SPY", "QQQ", "IWM", "TLT", "GLD", "EEM", "XLE"],
}
WINDOW = 63          # production: stock.history(period="3mo")
LOOKBACK_BARS = 252  # windows ending in the last year
OLD_RULES = {"munger_high": 3.0, "dalio_low": 2.0, "dalio_high": 5.0}
VOL_THRESHOLDS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60)


def fetch_bars(ticker: str, cache: Path) -> List[Dict[str, float]]:
    path = cache / f"{ticker}.json"
    if path.exists():
        return json.loads(path.read_text())
    import yfinance as yf

    hist = yf.Ticker(ticker).history(period="2y")
    bars = []
    for c, h, lo in zip(hist["Close"].tolist(), hist["High"].tolist(), hist["Low"].tolist()):
        if all(isinstance(v, float) and math.isfinite(v) for v in (c, h, lo)):
            bars.append({"c": c, "h": h, "l": lo})
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bars))
    return bars


def realised_vol(closes: List[float], ddof: int) -> float:
    rets = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 20, len(closes))]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - ddof)
    return math.sqrt(var) * math.sqrt(252)


def quantile(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolated quantile, q in [0, 1]."""
    if not sorted_vals:
        return float("nan")
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def rate(vals: List[float], pred) -> float:
    return sum(1 for v in vals if pred(v)) / len(vals) if vals else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--json", type=Path, help="write the summary here")
    args = ap.parse_args()
    socket.setdefaulttimeout(30)

    samples: Dict[str, List[Dict[str, float]]] = {g: [] for g in UNIVERSE}
    failed = []
    for group, tickers in UNIVERSE.items():
        for t in tickers:
            try:
                bars = fetch_bars(t, args.cache)
            except Exception as exc:  # network: report and continue
                failed.append(f"{t}: {exc}")
                continue
            if len(bars) < WINDOW + 1:
                failed.append(f"{t}: only {len(bars)} bars")
                continue
            start = max(WINDOW, len(bars) - LOOKBACK_BARS)
            for end in range(start, len(bars) + 1):
                win = bars[end - WINDOW:end]
                c = [b["c"] for b in win]
                h = [b["h"] for b in win]
                lo = [b["l"] for b in win]
                old = _calculate_technicals_from_prices(c)["atr"] / c[-1] * 100
                new = _calculate_technicals_from_prices(c, h, lo)["atr"] / c[-1] * 100
                samples[group].append({
                    "ticker": t, "old": old, "new": new,
                    "vol0": realised_vol(c, 0), "vol1": realised_vol(c, 1),
                })

    pooled = [s for g in samples.values() for s in g]
    old_all = [s["old"] for s in pooled]
    new_sorted = sorted(s["new"] for s in pooled)

    old_rates = {
        "munger_high": rate(old_all, lambda v: v > OLD_RULES["munger_high"]),
        "dalio_low": rate(old_all, lambda v: v < OLD_RULES["dalio_low"]),
        "dalio_high": rate(old_all, lambda v: v > OLD_RULES["dalio_high"]),
    }
    matched = {
        "munger_high": quantile(new_sorted, 1 - old_rates["munger_high"]),
        "dalio_low": quantile(new_sorted, old_rates["dalio_low"]),
        "dalio_high": quantile(new_sorted, 1 - old_rates["dalio_high"]),
    }

    def group_rows(thr: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        rows = {}
        for g, ss in list(samples.items()) + [("pooled", pooled)]:
            olds = [s["old"] for s in ss]
            news = [s["new"] for s in ss]
            rows[g] = {
                "n": len(ss),
                "median_ratio_new_over_old": median(
                    s["new"] / s["old"] for s in ss if s["old"] > 0),
                # high-vol windows: the ratio is lower there (gap days)
                "median_ratio_when_old>3": (median(
                    s["new"] / s["old"] for s in ss if s["old"] > 3)
                    if any(s["old"] > 3 for s in ss) else None),
                "median_old_pct": median(olds),
                "median_new_pct": median(news),
                "old>3": rate(olds, lambda v: v > 3),
                "old<2": rate(olds, lambda v: v < 2),
                "old>5": rate(olds, lambda v: v > 5),
                "true>3 (unchanged thr)": rate(news, lambda v: v > 3),
                "true<2 (unchanged thr)": rate(news, lambda v: v < 2),
                "true>5 (unchanged thr)": rate(news, lambda v: v > 5),
                "true>munger_new": rate(news, lambda v: v > thr["munger_high"]),
                "true<dalio_low_new": rate(news, lambda v: v < thr["dalio_low"]),
                "true>dalio_high_new": rate(news, lambda v: v > thr["dalio_high"]),
            }
        return rows

    # Proposed thresholds = matched quantiles rounded to 0.25 percentage point.
    proposed = {k: round(v * 4) / 4 for k, v in matched.items()}

    news_all = [s["new"] for s in pooled]
    grid = {
        "munger_high": [5.0, 5.5, 5.75, 6.0],
        "dalio_low": [3.0, 3.5, 3.75, 4.0],
        "dalio_high": [8.0, 8.5, 9.0, 9.25, 9.5, 10.0],
    }
    candidates = {
        k: {str(t): rate(news_all, (lambda v, t=t: v < t) if k == "dalio_low"
                          else (lambda v, t=t: v > t)) for t in ts}
        for k, ts in grid.items()
    }

    vol_cross = sum(
        1 for s in pooled
        if any((s["vol0"] > t) != (s["vol1"] > t) for t in VOL_THRESHOLDS)
    )
    summary = {
        "n_windows": len(pooled),
        "n_tickers": sum(len({s["ticker"] for s in g}) for g in samples.values()),
        "failed": failed,
        "old_rates_pooled": old_rates,
        "matched_quantile_thresholds": matched,
        "proposed_thresholds": proposed,
        "candidate_rates_pooled": candidates,
        "by_group_proposed": group_rows(proposed),
        "vol_ddof1_over_ddof0": median(s["vol1"] / s["vol0"] for s in pooled if s["vol0"] > 0),
        "vol_threshold_crossings": vol_cross,
        "vol_threshold_crossing_rate": vol_cross / len(pooled) if pooled else float("nan"),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    print(text)
    if args.json:
        args.json.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
