# -*- coding: utf-8 -*-
"""R5: generate ``feedback/agent_correlation.json`` from real backtest data.

Before this script, the diversity-penalty logic in
``ConsensusEngine.get_consensus`` (``src/augur/consensus/engine.py``, "---
Correlation diversity penalty ---") silently no-opped for every install,
because nothing ever produced ``feedback/agent_correlation.json`` --  only
``feedback/agent_correlation.json.example`` (hand-picked illustrative
numbers) shipped, and a user had to manually copy it to activate the
penalty. This script computes the real pairwise correlation matrix from
actual agent behavior and writes it directly, so the diversity penalty is
backed by real data out of the box.

This is NOT part of the pytest suite (it makes many live network calls to
SEC EDGAR + yfinance over a multi-ticker, multi-year universe). Run it
manually:

    .venv/bin/python scripts/generate_agent_correlation.py

Method
------
Reuses the exact same real-data machinery already validated by
``scripts/regime_weight_oos.py`` (Phase D): ``fetch_ticker_replay_records``
for point-in-time price + EDGAR fundamentals, and ``_signed_agent_scores``
for the signed (bullish=+score, bearish=-score, neutral=0) per-agent score
convention. For every (ticker, date) with sufficient point-in-time data,
every agent is run once; only points where every agent produced a score
are kept, so all per-agent vectors stay aligned for correlation. Pearson
correlation is computed for every ordered agent pair from these aligned
vectors -- this measures whether two agents' *signed views* move together
across real historical (ticker, date) points, which is exactly what the
diversity penalty needs (agents that are highly correlated add little
independent information to the consensus).

Honest scope note: correlation is pooled across the whole universe/window,
not conditioned on regime or sector -- a coarser statistic than the
regime-bucketed cross-sectional IC work, but adequate for a diversity
penalty (which itself is a single global pairwise matrix, not
regime/sector-aware).
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from augur.backtest import fetch_ticker_replay_records, _signed_agent_scores  # noqa: E402
from augur.registry import AgentRegistry  # noqa: E402
from _replay_universe import UNIVERSE, START, END  # noqa: E402

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "feedback" / "agent_correlation.json"


def _pearson(x, y) -> float:
    """Pure-Python Pearson correlation; returns 0.0 if either series has zero variance."""
    n = len(x)
    if n < 3:
        return 0.0
    mean_x = statistics.fmean(x)
    mean_y = statistics.fmean(y)
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)
    if var_x <= 0 or var_y <= 0:
        return 0.0
    return cov / (var_x ** 0.5 * var_y ** 0.5)


def main() -> None:
    print(f"Universe: {len(UNIVERSE)} tickers")
    print(f"Window: {START} .. {END}")

    registry = AgentRegistry()
    agents = registry.get_all()
    agent_ids = [a.agent_id for a in agents]
    print(f"Agents: {len(agent_ids)} -- {agent_ids}")

    per_agent_scores = {aid: [] for aid in agent_ids}
    n_points_total = 0
    n_points_aligned = 0

    for ticker in UNIVERSE:
        recs = fetch_ticker_replay_records(ticker, START, END)
        print(f"  {ticker}: {len(recs)} PIT records")
        for rec in recs:
            n_points_total += 1
            scores = _signed_agent_scores(ticker, rec, agents)
            if len(scores) != len(agent_ids):
                continue  # one or more agents errored -- drop to keep vectors aligned
            n_points_aligned += 1
            for aid in agent_ids:
                per_agent_scores[aid].append(scores[aid])

    print(f"\nTotal (ticker, date) points: {n_points_total}")
    print(f"Aligned points (all {len(agent_ids)} agents scored): {n_points_aligned}")
    if n_points_aligned < 30:
        print("WARNING: fewer than 30 aligned points -- correlation estimates will be noisy. "
              "Writing the file anyway; re-run with a wider window/universe to firm up.")

    print("\nComputing pairwise Pearson correlation...")
    correlation_matrix = {}
    for i, aid_a in enumerate(agent_ids):
        correlation_matrix[aid_a] = {}
        for aid_b in agent_ids:
            if aid_a == aid_b:
                continue
            corr = _pearson(per_agent_scores[aid_a], per_agent_scores[aid_b])
            correlation_matrix[aid_a][aid_b] = round(corr, 4)

    high_pairs = sorted(
        (
            (aid_a, aid_b, corr)
            for aid_a, row in correlation_matrix.items()
            for aid_b, corr in row.items()
            if aid_a < aid_b and corr > 0.7
        ),
        key=lambda t: -t[2],
    )
    print(f"\nPairs with corr > 0.7 (these are the ones the diversity penalty actually acts on):")
    for aid_a, aid_b, corr in high_pairs:
        print(f"  {aid_a:<16}{aid_b:<16}{corr:.4f}")
    if not high_pairs:
        print("  (none)")

    output = {
        "_comment": "Pairwise agent signal correlation for diversity penalty. "
                    "Generated by scripts/generate_agent_correlation.py -- do not hand-edit.",
        "_format": "correlation_matrix[agent_a][agent_b] in [-1, 1]; only pairs with corr > 0.7 reduce weight.",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "generate_agent_correlation.py",
        "n_observations": n_points_aligned,
        "universe_size": len(UNIVERSE),
        "window": f"{START}..{END}",
        "correlation_matrix": correlation_matrix,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
