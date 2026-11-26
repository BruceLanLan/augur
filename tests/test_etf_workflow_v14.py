# -*- coding: utf-8 -*-
"""v14: `augur committee` and `augur workflow` must not print the withheld
fund consensus as a raw neutral 5.0/10, and abstaining personas must not be
counted as neutral votes. Contexts are hand-built; no network."""

from unittest.mock import patch

from click.testing import CliRunner

from augur.cli import main
from tests.test_etf_output import aapl_ctx, fake_learning, fetch_returns, spy_ctx  # noqa: F401


def _run(args):
    return CliRunner().invoke(main, args, catch_exceptions=False)


def test_committee_etf_shows_withheld(fetch_returns, fake_learning):  # noqa: F811
    fetch_returns["SPY"] = spy_ctx
    with patch.dict("os.environ", {"AUGUR_SKIP_MACRO_FETCH": "1"}):
        result = _run(["committee", "SPY"])
    out = result.output
    assert result.exit_code == 0, out
    assert "WITHHELD" in out
    assert "Score:       5.0/10" not in out
    assert "ABSTAIN" in out
    assert "Abstain 17" in out
    assert "PE=0.0" not in out


def test_committee_equity_unchanged(fetch_returns, fake_learning):  # noqa: F811
    fetch_returns["AAPL"] = aapl_ctx
    with patch.dict("os.environ", {"AUGUR_SKIP_MACRO_FETCH": "1"}):
        result = _run(["committee", "AAPL"])
    out = result.output
    assert result.exit_code == 0, out
    assert "WITHHELD" not in out
    assert "ABSTAIN" not in out
    assert "Score:" in out


def test_workflow_summary_etf_withheld(fetch_returns, fake_learning):  # noqa: F811
    from augur.workflow import run_workflow

    fetch_returns["SPY"] = spy_ctx
    with patch.dict("os.environ", {"AUGUR_SKIP_MACRO_FETCH": "1"}):
        result = run_workflow("SPY", steps="fetch,analyze,consensus,committee")
    cons = result["results"]["consensus"]
    assert cons["withheld"] is True
    assert cons["kelly_pct"] == 0.0
    committee = result["results"]["committee"]
    assert committee["verdict"] == "withheld"
    assert committee["score"] is None
    assert committee["abstained"] == 17
    assert sum(committee["vote"].values()) == 1
    summary = result["summary"]
    assert "WITHHELD" in summary
    assert "Score: 5.0/10" not in summary


def test_format_summary_equity_consensus_unchanged():
    from augur.workflow import format_workflow_summary

    text = format_workflow_summary({
        "ticker": "AAPL", "steps": ["consensus"],
        "results": {"consensus": {"signal": "bullish", "score": 7.2, "confidence": 0.6}},
    })
    assert "Signal: BULLISH  Score: 7.2/10" in text


def test_stock_page_handles_withheld_consensus():
    from pathlib import Path

    import augur

    html = (Path(augur.__file__).parent.parent / "dashboard" / "templates"
            / "stocks.html").read_text(encoding="utf-8")
    assert "function consensusWithheld(cons)" in html
    assert "cons.metadata.consensus_withheld" in html
    assert "'WITHHELD'" in html
    # Abstaining personas are not counted as neutral votes, and their
    # persona cards show N/A instead of a 5.0 score.
    assert "a.metadata.not_applicable" in html
    assert "function _abstained(a)" in html


def test_workflow_summary_lists_abstainers_and_fund_type(fetch_returns, fake_learning):  # noqa: F811
    from augur.workflow import run_workflow

    fetch_returns["SPY"] = spy_ctx
    with patch.dict("os.environ", {"AUGUR_SKIP_MACRO_FETCH": "1"}):
        result = run_workflow("SPY", steps="fetch,analyze,consensus")
    assert result["results"]["fetch"]["asset_type"] == "etf"
    analyze = result["results"]["analyze"]
    assert sum(1 for a in analyze.values() if a.get("abstained")) == 17
    summary = result["summary"]
    assert "Type: ETF" in summary
    assert "PE: 0.0" not in summary
    assert "Abstained (17" in summary


def _fund_bundle():
    personas = {f"p{i}": {"signal": "neutral", "score": 5.0, "abstained": True} for i in range(17)}
    personas["dalio"] = {"signal": "neutral", "score": 5.4, "confidence": 0.5}
    return {
        "step_results": [
            {"step_name": "analyze", "status": "success", "result": personas},
            {"step_name": "consensus", "status": "success",
             "result": {"signal": "neutral", "score": 5.0, "confidence": 0.0,
                        "withheld": True, "withheld_reason": "too few applicable"}},
        ],
    }


def test_disagreement_from_fund_bundle_is_not_divided():
    from augur.disagreement import build_disagreement_from_bundle

    dm = build_disagreement_from_bundle(_fund_bundle(), "SPY", "run_SPY_x")
    assert dm.consensus_strength == "n/a"
    assert "17 abstained" in dm.summary


def test_report_from_run_fund_shows_withheld(monkeypatch):
    import augur.run_tracker as rt

    monkeypatch.setattr(rt, "latest_run_id", lambda *a, **k: "run_SPY_x")
    monkeypatch.setattr(rt, "load_run_bundle_dict", lambda run_id: _fund_bundle())
    result = _run(["report", "from-run", "SPY"])
    out = result.output
    assert result.exit_code == 0, out
    assert "withheld (no consensus signal)" in out
    assert "5.00 / 10" not in out
    assert "neutral 1 /" in out
    assert "abstained**: 17" in out
