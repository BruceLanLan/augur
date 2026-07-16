# -*- coding: utf-8 -*-
"""B2: which of the ~70 persona factors (18 personas x metadata["factors"])
actually carry cross-sectional predictive signal, vs. which are noise?

This is NOT part of the pytest suite (it makes many live network calls to
EDGAR/yfinance over a 37-ticker, multi-year universe and reports numbers
rather than asserting pass/fail) -- same convention as
scripts/regime_weight_oos.py and scripts/generate_agent_correlation.py. Run
it manually:

    .venv/bin/python scripts/factor_attribution.py

Background
----------
Every persona's compute() derives a "factors" dict (e.g. Buffett's "moat",
Graham's "safety_margin") purely from MarketContext -- no network calls
inside persona logic. That means every one of these ~70 factor values is
replayable at any historical (ticker, date) the same way
scripts/regime_weight_oos.py replays agent consensus scores: build a
MarketContext from fetch_ticker_replay_records()'s point-in-time EDGAR
fundamentals, run every agent once, and read metadata["factors"] instead of
just the final score.

Two EDGAR-derived factors are NOT covered here and that is a real, not
incidental, scope boundary: insider_buying_signal
(augur.consensus.edgar_insider) and institutional_flow_signal
(augur.consensus.edgar_institutional) are point-in-time capable in
principle (both take an as_of_date), but neither is wired into any
persona's compute()/metadata["factors"] as of v10.12.0 -- grep confirms no
caller outside their own modules. Attributing them would require a
separate, additional real-network pull (Form 4 / 13F history per ticker per
date) on top of the fundamentals pull this script already does; left out of
this pass to keep scope to "factors personas already emit today."

Multiple-comparison discipline (read before trusting any single number)
------------------------------------------------------------------------
With ~100 factor keys (18 personas x several factors each) tested against
one window, some will show a "significant" whole-window IC by chance alone
-- this project's own regime-weights episode
(docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md) is the concrete precedent for
exactly this trap. compute_factor_cross_sectional_ic splits the qualifying
days in half chronologically and flags split_half_stable=True only when
both halves clear a minimum |IC| and agree in sign. Only treat
split_half_stable=True factors as candidate findings; everything else is
printed for completeness, not as evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from augur.backtest import fetch_ticker_replay_records, compute_factor_cross_sectional_ic  # noqa: E402
from augur.registry import AgentRegistry  # noqa: E402
from _replay_universe import UNIVERSE, START, END  # noqa: E402


def main() -> None:
    print(f"Universe: {len(UNIVERSE)} tickers")
    print(f"Window: {START} .. {END}")

    registry = AgentRegistry()
    agents = registry.get_all()
    print(f"Agents: {len(agents)}")

    print(f"\nFetching point-in-time replay records for {len(UNIVERSE)} tickers "
          f"(same pull as regime_weight_oos.py; can take a while)...")
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

    print("\nComputing cross-sectional per-factor IC "
          "(this runs every agent on every ticker/day -- slower than "
          "regime_weight_oos.py's per-agent-only pass)...")
    result = compute_factor_cross_sectional_ic(records_by_ticker, agents)

    print(f"\nQualifying days (>= 5 tickers with PIT data): {result['n_days_total']}")
    print(f"Days skipped as too thin: {result['n_days_skipped_thin']}")
    print(f"Distinct factor keys observed: {len(result['per_factor'])}")

    stable = {k: v for k, v in result["per_factor"].items() if v["split_half_stable"]}
    unstable = {k: v for k, v in result["per_factor"].items() if not v["split_half_stable"]}

    print(f"\n=== Split-half STABLE factors ({len(stable)}) -- candidate findings ===")
    print(f"{'factor':<40}{'ic_mean':>10}{'1st_half':>12}{'2nd_half':>12}{'n_days':>8}")
    for key, stats in sorted(stable.items(), key=lambda kv: -abs(kv[1]["ic_mean"])):
        print(f"{key:<40}{stats['ic_mean']:>10.4f}{stats['first_half_ic']:>12.4f}"
              f"{stats['second_half_ic']:>12.4f}{stats['n_days']:>8}")

    print(f"\n=== Top 15 by |whole-window IC| regardless of stability "
          f"(diagnostic only, {len(unstable)} unstable factors exist) ===")
    print(f"{'factor':<40}{'ic_mean':>10}{'stable':>8}{'n_days':>8}")
    for key, stats in sorted(
        result["per_factor"].items(), key=lambda kv: -abs(kv[1]["ic_mean"])
    )[:15]:
        print(f"{key:<40}{stats['ic_mean']:>10.4f}{str(stats['split_half_stable']):>8}"
              f"{stats['n_days']:>8}")

    print(
        "\n"
        "=== Honest summary (read this before drawing any conclusion) ===\n"
        "This script measures per-factor cross-sectional rank-IC for every\n"
        "numeric value in every persona's metadata['factors'] output, using\n"
        "real point-in-time EDGAR fundamentals (no look-ahead; days without\n"
        "as-of-available fundamentals are dropped, never zero-filled).\n"
        "\n"
        "Only 'split-half STABLE' factors above are candidate findings --\n"
        "the rest are printed for completeness but are exactly the kind of\n"
        "number that produced a false-positive 'the regime weights work'\n"
        "conclusion in this project before (see\n"
        "docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md, later reversed by\n"
        "scripts/regime_weight_oos.py's honest OOS validation). Do not act\n"
        "on an unstable factor's whole-window IC number alone.\n"
        "\n"
        "insider_buying_signal and institutional_flow_signal are NOT\n"
        "represented in this output -- neither is wired into any persona's\n"
        "metadata['factors'] as of v10.12.0, see this file's module\n"
        "docstring for why."
    )


if __name__ == "__main__":
    main()
