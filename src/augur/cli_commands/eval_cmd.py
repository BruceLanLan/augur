# -*- coding: utf-8 -*-
"""Evaluation CLI — score personas against realised returns from backtest records.

Wires two previously unreachable modules to data that already exists after
`augur backtest TICKER`:

* ``augur eval personas`` — consensus IC and hit rate, plus leave-one-out
  ablation per persona (augur.eval_lab.ChronologicalEvaluator).
* ``augur eval factors`` — each persona's score treated as a factor, IC mean /
  t-stat / p-value over time chunks (augur.prompt_eval.FactorLab).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import click

MIN_DATES = 20
_HORIZONS = {"5": "actual_return_5d", "20": "actual_return_20d", "60": "actual_return_60d"}


def _load_panel(ticker: str, horizon: str, include_demo: bool) -> Tuple[List[str], Dict[str, Dict[str, float]], Dict[str, float]]:
    """Return (dates, scores[agent][date], forward_return[date]) from backtest records."""
    from augur.backtest import Backtester

    field = _HORIZONS[horizon]
    records = Backtester().load_records(ticker=ticker)
    if not include_demo:
        records = [r for r in records if r.data_source == "live"]
    scores: Dict[str, Dict[str, float]] = {}
    returns: Dict[str, float] = {}
    for r in records:  # later records for the same (agent, date) win
        scores.setdefault(r.agent_id, {})[r.date] = float(r.score)
        returns[r.date] = float(getattr(r, field))
    dates = sorted(d for d in returns if all(d in s for s in scores.values()))
    return dates, scores, returns


def _require_numpy():
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        click.echo("Error: evaluation needs numpy — pip install 'augur-agents[data]'", err=True)
        raise SystemExit(1)


def _panel_or_exit(ticker, horizon, include_demo):
    dates, scores, returns = _load_panel(ticker, horizon, include_demo)
    if len(dates) < MIN_DATES or len(scores) < 2:
        source = "backtest records" if include_demo else "live (non-demo) backtest records"
        click.echo(
            f"Not enough data: {len(dates)} dated observations across {len(scores)} personas in {source} "
            f"for {ticker.upper()} (need ≥{MIN_DATES} dates and ≥2 personas).\n"
            f"Run `augur backtest {ticker.upper()} --days 120` first."
        )
        raise SystemExit(1)
    return dates, scores, returns


@click.group("eval")
def eval_cmd():
    """Evaluate persona predictions against realised returns (from `augur backtest`)."""


@eval_cmd.command("personas")
@click.argument("ticker")
@click.option("--horizon", type=click.Choice(sorted(_HORIZONS, key=int)), default="20", show_default=True,
              help="Forward-return horizon in trading days.")
@click.option("--include-demo", is_flag=True, help="Also use synthetic --demo records (not a real track record).")
def eval_personas_cmd(ticker, horizon, include_demo):
    """Consensus IC / hit rate and each persona's leave-one-out contribution."""
    _require_numpy()
    import numpy as np

    from augur.eval_lab import ChronologicalEvaluator as E

    dates, scores, returns = _panel_or_exit(ticker, horizon, include_demo)
    agents = sorted(scores)
    matrix = np.array([[scores[a][d] for d in dates] for a in agents])  # agents x dates
    fwd = np.array([returns[d] for d in dates])
    consensus = matrix.mean(axis=0)
    full_ic = E.compute_ic(consensus, fwd)
    hit = E.compute_accuracy(consensus / 10.0, (fwd > 0).astype(float))

    click.echo(f"═══ Persona evaluation: {ticker.upper()} · {horizon}d forward returns ═══")
    click.echo(f"  Observations: {len(dates)} dates ({dates[0]} → {dates[-1]}), {len(agents)} personas"
               + ("" if not include_demo else "  [includes synthetic demo records]"))
    click.echo(f"  Equal-weight consensus IC: {full_ic:+.3f}   hit rate (score ≥5 vs return >0): {hit:.0%}")
    click.echo("\n  Leave-one-out: IC change when the persona is removed (negative = persona helps)")
    rows, constant = [], []
    for i, agent in enumerate(agents):
        if np.ptp(matrix[i]) < 1e-9:
            # A constant score shifts the consensus without changing its ranking;
            # any bootstrap "significance" here is floating-point noise.
            constant.append(agent)
            continue
        without = np.delete(matrix, i, axis=0).mean(axis=0)
        ic_without = E.compute_ic(without, fwd)
        significant = E.check_significance_ic(consensus, without, fwd, n_bootstrap=500)
        rows.append((agent, ic_without - full_ic, E.compute_ic(matrix[i], fwd), significant))
    for agent, delta, own_ic, significant in sorted(rows, key=lambda r: r[1]):
        flag = "  *" if significant and abs(delta) > 1e-6 else ""
        click.echo(f"  {agent:<16} ΔIC {delta:+.3f}   own IC {own_ic:+.3f}{flag}")
    if constant:
        click.echo(f"  constant score in this window (no information): {', '.join(constant)}")
    click.echo("\n  * bootstrap 95% CI of ΔIC excludes 0. Forward returns overlap day to day, so")
    click.echo("    intervals are optimistic; treat this as a screen, not a validated weight.")


@eval_cmd.command("factors")
@click.argument("ticker")
@click.option("--horizon", type=click.Choice(sorted(_HORIZONS, key=int)), default="20", show_default=True)
@click.option("--periods", default=5, show_default=True, help="Time chunks for the IC t-test.")
@click.option("--include-demo", is_flag=True, help="Also use synthetic --demo records.")
def eval_factors_cmd(ticker, horizon, periods, include_demo):
    """Treat each persona's score as a factor: IC mean, t-stat and p-value over time."""
    _require_numpy()
    import numpy as np

    from augur.prompt_eval import FactorLab

    dates, scores, returns = _panel_or_exit(ticker, horizon, include_demo)
    fwd = np.array([returns[d] for d in dates])
    factor_scores = {a: np.array([scores[a][d] for d in dates]) for a in sorted(scores)}
    constant = sorted(a for a, v in factor_scores.items() if np.ptp(v) < 1e-9)
    results = FactorLab.evaluate_factors(
        {a: v for a, v in factor_scores.items() if a not in constant}, fwd, periods=periods,
    )

    click.echo(f"═══ Factor lab: {ticker.upper()} · {horizon}d forward returns · {len(dates)} dates in {periods} chunks ═══")
    click.echo(f"  {'factor':<16} {'IC mean':>8} {'IC std':>7} {'t':>6} {'p':>6}  sig")
    for r in results:
        click.echo(f"  {r.factor_name:<16} {r.ic_mean:>+8.3f} {r.ic_std:>7.3f} {r.t_stat:>6.2f} {r.p_value:>6.3f}  {'yes' if r.significant else ''}")
    if constant:
        click.echo(f"  constant score in this window (no information): {', '.join(constant)}")
    click.echo("\n  Single-ticker time-series IC with overlapping forward returns: a screen for")
    click.echo("  stability, not evidence that a persona predicts returns across stocks.")
