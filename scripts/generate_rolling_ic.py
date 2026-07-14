# -*- coding: utf-8 -*-
"""B1: generate ``feedback/rolling_ic.json`` from real backtest data.

Before this script, the rolling-IC dynamic weight override in
``ConsensusEngine.get_consensus`` (``src/augur/consensus/engine.py``,
``load_rolling_ic_weights()`` / the ``0.5 * w + 0.5 * rolling_ic_weights[...]``
blend) silently no-opped for every install, because nothing ever produced
``feedback/rolling_ic.json`` -- only ``feedback/rolling_ic.json.example``
(hand-picked illustrative numbers) shipped. This is the exact same gap R5
found and fixed for ``feedback/agent_correlation.json``
(``scripts/generate_agent_correlation.py``) -- this script closes the
analogous gap for rolling IC, reusing the same real-data machinery.

This is NOT part of the pytest suite (it makes many live network calls to
SEC EDGAR + yfinance over a multi-ticker, multi-year universe, and reports
numbers rather than asserting pass/fail). Run it manually:

    .venv/bin/python scripts/generate_rolling_ic.py

Method
------
Reuses ``compute_cross_sectional_regime_ic`` (already shipped for Phase D's
regime-weight validation) purely for the per-agent daily cross-sectional IC
it already computes as a byproduct -- this script does NOT use or write
anything about the regime-weighted vs flat consensus comparison that
function's return value is centered on. Per-agent IC is aggregated across
all regime buckets, weighted by each bucket's day count, into one overall
IC per agent for the whole window.

IC -> weight transform (read before trusting the numbers)
-----------------------------------------------------------
Raw cross-sectional IC values are typically small (a real IC of +/-0.05 to
+/-0.15 is a meaningfully strong signal in this domain -- see
``regime_weight_oos.py`` and ``factor_attribution.py``'s real-data output
for reference magnitudes) and can be negative (anti-predictive). The
consuming code in ``engine.py`` normalizes whatever weights this script
writes to sum to 1.0 and blends them 50/50 with each agent's base weight,
so raw IC values cannot be used directly -- a small linear rescale centers
IC=0 at weight=0.5 and clamps to ``[0.1, 3.0]``, the exact same clamp
``LearningEngine`` already uses for its own IC-derived weights
(``src/augur/learning.py``), for consistency between the two IC-driven
weighting mechanisms in this codebase:

    weight = clamp(0.5 + ic * 5.0, 0.1, 3.0)

This is a deliberate, documented choice, not a principled optimum -- an
agent with IC=-0.08 (meaningfully anti-predictive) still gets the 0.1 floor
rather than being zeroed out entirely, matching how LearningEngine already
handles this same tradeoff.

Honest scope note, same discipline as B2's factor_attribution.py
------------------------------------------------------------------
This script does NOT split the window in half to check stability the way
``compute_factor_cross_sectional_ic`` does -- per-agent IC (18 values) is a
much smaller multiple-comparison surface than per-factor IC (~90 values),
and this project's own precedent (R5's agent_correlation, which also
doesn't split-half) treats a single full-window statistic as adequate for
this class of coarse, whole-portfolio-level weight. If a future pass wants
to add that rigor here too, it is a natural follow-up, not a correctness
gap in what ships today.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")

from augur.backtest import (  # noqa: E402
    build_date_to_regime,
    fetch_ticker_replay_records,
    compute_cross_sectional_regime_ic,
)
from augur.registry import AgentRegistry  # noqa: E402

# Same 37-ticker cross-sector universe as regime_weight_oos.py /
# generate_agent_correlation.py / factor_attribution.py, so this run reuses
# their already-warm EDGAR/price caches.
UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AMD", "CRM", "ORCL", "ADBE",
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP",
    "XOM", "CVX", "COP", "SLB",
    "KO", "PG", "WMT", "COST", "MCD", "PEP",
    "JNJ", "PFE", "UNH", "MRK", "ABBV", "LLY",
    "CAT", "BA", "HON", "GE",
]

START = "2022-01-01"
END = "2026-06-01"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "feedback" / "rolling_ic.json"


def ic_to_weight(ic: float) -> float:
    """Linear rescale + clamp, matching LearningEngine's own IC-derived
    weight clamp ([0.1, 3.0]) for consistency between the two IC-driven
    weighting mechanisms in this codebase. See module docstring."""
    return max(0.1, min(3.0, 0.5 + ic * 5.0))


def aggregate_overall_ic(per_agent_by_regime: dict, per_regime: dict) -> dict:
    """Weighted-average each agent's per-regime cross-sectional IC into one
    overall IC, weighted by each regime bucket's day count."""
    agent_ids = sorted({aid for bucket in per_agent_by_regime.values() for aid in bucket})
    overall: dict = {}
    for aid in agent_ids:
        weighted_sum = 0.0
        total_days = 0
        for regime, bucket in per_agent_by_regime.items():
            if aid not in bucket:
                continue
            n_days = per_regime.get(regime, {}).get("n_days", 0)
            weighted_sum += bucket[aid] * n_days
            total_days += n_days
        overall[aid] = weighted_sum / total_days if total_days else 0.0
    return overall


def main() -> None:
    print(f"Universe: {len(UNIVERSE)} tickers")
    print(f"Window: {START} .. {END}")

    print("\nBuilding date_to_regime (one VIX+SPY pull for the whole window)...")
    date_to_regime = build_date_to_regime(START, END)

    print(f"\nFetching point-in-time replay records for {len(UNIVERSE)} tickers "
          f"(reuses the same pull as regime_weight_oos.py; can take a while)...")
    records_by_ticker = {}
    for ticker in UNIVERSE:
        recs = fetch_ticker_replay_records(ticker, START, END)
        records_by_ticker[ticker] = recs
        print(f"  {ticker}: {len(recs)} records")

    total_records = sum(len(v) for v in records_by_ticker.values())
    print(f"\nTotal records across universe: {total_records}")

    print("\nComputing per-agent cross-sectional IC by regime...")
    result = compute_cross_sectional_regime_ic(records_by_ticker, date_to_regime)
    print(f"Qualifying days: {result['n_days_total']}  "
          f"(skipped as too thin: {result['n_days_skipped_thin']})")

    overall_ic = aggregate_overall_ic(result["per_agent_by_regime"], result["per_regime"])

    print(f"\n{'agent':<16}{'overall_ic':>12}{'weight':>10}")
    weights = {}
    for aid, ic in sorted(overall_ic.items(), key=lambda kv: -kv[1]):
        w = ic_to_weight(ic)
        weights[aid] = round(w, 4)
        print(f"{aid:<16}{ic:>12.4f}{w:>10.4f}")

    output = {
        "_comment": "Rolling information-coefficient weights per agent. "
                    "Generated by scripts/generate_rolling_ic.py -- do not hand-edit.",
        "_format": "Higher IC -> higher weight; normalized at runtime when blended 50/50 with base weights.",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "generate_rolling_ic.py",
        "n_days": result["n_days_total"],
        "universe_size": len(UNIVERSE),
        "window": f"{START}..{END}",
        "weights": weights,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")

    print(
        "\n"
        "=== Honest summary ===\n"
        "These weights are a whole-window (not split-half validated) "
        "aggregate of real per-agent cross-sectional IC. Whether blending "
        "them 50/50 into the base consensus weight actually improves "
        "cross-sectional prediction quality vs. pure industry weights has "
        "NOT been validated here -- that would need the same kind of "
        "before/after OOS comparison regime_weight_oos.py did for regime "
        "multipliers (which, after real validation, turned out not to "
        "help and were disabled in v10.6.0). Writing this file makes the "
        "existing 50/50 blend in engine.py stop being a silent no-op; it "
        "does not by itself establish that the blend helps."
    )


if __name__ == "__main__":
    main()
