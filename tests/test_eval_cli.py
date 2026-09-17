# -*- coding: utf-8 -*-
"""`augur eval personas|factors` on backtest records (eval_lab / prompt_eval had no entry point)."""
import json
import random

import pytest
from click.testing import CliRunner


@pytest.fixture
def records_file(tmp_path, monkeypatch):
    from augur.backtest import Backtester

    path = tmp_path / "records.jsonl"
    monkeypatch.setattr(Backtester, "RECORDS_DIR", tmp_path)
    monkeypatch.setattr(Backtester, "RECORDS_FILE", path)
    return path


def _write(path, n_dates, source="live", informative="buffett"):
    rng = random.Random(7)
    lines = []
    for day in range(n_dates):
        date = f"2026-{1 + day // 28:02d}-{1 + day % 28:02d}"
        ret = rng.uniform(-0.1, 0.1)
        for agent in ("buffett", "graham", "cathie_wood", "fisher"):
            if agent == "fisher":
                score = 6.0  # quarterly fundamentals: constant through a daily replay
            elif agent == informative:
                score = 5 + 40 * ret + rng.gauss(0, 0.6)
            else:
                score = rng.uniform(2, 8)
            lines.append(json.dumps({
                "date": date, "ticker": "EVL", "agent_id": agent, "signal": "neutral",
                "score": score, "confidence": 0.5, "actual_return_20d": ret, "data_source": source,
            }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run(*args):
    from augur.cli import main

    return CliRunner().invoke(main, list(args))


def test_personas_ranks_the_informative_persona_as_most_helpful(records_file):
    _write(records_file, 60)
    result = _run("eval", "personas", "EVL")

    assert result.exit_code == 0, result.output
    assert "Observations: 60 dates" in result.output
    loo = result.output.split("Leave-one-out")[1].splitlines()
    first_row = next(line for line in loo if line.strip().startswith(("buffett", "graham", "cathie_wood")))
    assert first_row.strip().startswith("buffett"), result.output


def test_factors_flags_the_informative_persona_as_significant(records_file):
    _write(records_file, 60)
    result = _run("eval", "factors", "EVL", "--periods", "5")

    assert result.exit_code == 0, result.output
    buffett = next(line for line in result.output.splitlines() if line.strip().startswith("buffett"))
    assert buffett.rstrip().endswith("yes"), result.output


def test_demo_records_are_excluded_unless_requested(records_file):
    _write(records_file, 60, source="demo")
    refused = _run("eval", "personas", "EVL")
    assert refused.exit_code == 1
    assert "Not enough data: 0 dated observations" in refused.output
    assert _run("eval", "personas", "EVL", "--include-demo").exit_code == 0


def test_too_few_dates_is_explained(records_file):
    _write(records_file, 5)
    result = _run("eval", "factors", "EVL")
    assert result.exit_code == 1
    assert "augur backtest EVL" in result.output


def test_factorlab_pvalue_matches_student_t_without_scipy():
    """The no-scipy fallback used a normal approximation: df=4, t=2.0 gave
    p=0.045 (significant) instead of 0.116."""
    from augur.prompt_eval import FactorLab

    for t, df, expected in ((2.0, 4, 0.1161), (12.7062, 1, 0.05), (2.2281, 10, 0.05), (2.0, 100, 0.0482)):
        assert FactorLab._t_test_pvalue(t, df) == pytest.approx(expected, abs=5e-4)


def test_factorlab_constant_nonzero_ic_is_significant():
    import numpy as np

    from augur.prompt_eval import FactorLab

    fwd = np.linspace(-1, 1, 40)
    [perf] = FactorLab.evaluate_factors({"perfect": fwd * 3}, fwd, periods=4)
    assert perf.ic_mean == pytest.approx(1.0)
    assert perf.significant and perf.p_value < 1e-12


def test_constant_score_personas_are_labelled_not_ranked(records_file):
    _write(records_file, 60)
    for cmd in ("personas", "factors"):
        result = _run("eval", cmd, "EVL")
        assert result.exit_code == 0, result.output
        assert "constant score in this window (no information): fisher" in result.output
        assert not any(line.strip().startswith("fisher ") for line in result.output.splitlines())
