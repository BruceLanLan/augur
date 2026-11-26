"""v14.1 leftovers: abstention reasons split everywhere, dividend-yield units."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from augur.cli import main
from augur.consensus_display import abstained_label, split_abstained
from augur.datasources.yfinance_provider import dividend_yield_from_info
from tests.test_etf_output import spy_ctx_no_technicals  # noqa: F401


# --------------------------------------------------------------------------
# Abstention reasons
# --------------------------------------------------------------------------

def _mixed_bundle():
    personas = {f"p{i:02d}": {"signal": "neutral", "score": 5.0, "abstained": True,
                              "abstain_reason": "fund"} for i in range(14)}
    for aid in ("arps", "marks", "soros"):
        personas[aid] = {"signal": "neutral", "score": 5.0, "abstained": True,
                         "abstain_reason": "fund_data_missing"}
    personas["dalio"] = {"signal": "neutral", "score": 5.4, "confidence": 0.5}
    return {
        "step_results": [
            {"step_name": "analyze", "status": "success", "result": personas},
            {"step_name": "consensus", "status": "success",
             "result": {"signal": "neutral", "score": 5.0, "confidence": 0.0,
                        "withheld": True, "withheld_reason": "too few applicable"}},
        ],
    }


def test_split_abstained_dicts_and_legacy_records():
    no_rules, no_data = split_abstained({
        "a": {"abstained": True, "abstain_reason": "fund"},
        "b": {"abstained": True},  # pre-14.1 bundle: no reason recorded
        "c": {"abstained": True, "abstain_reason": "fund_data_missing"},
        "d": {"signal": "neutral", "score": 5.0},
    })
    assert no_rules == ["a", "b"] and no_data == ["c"]
    assert abstained_label(no_rules, []) == "rules not applicable to funds: a, b"
    assert abstained_label(no_rules, no_data) == (
        "2 rules not applicable to funds: a, b; 1 fund technicals missing: c")


def test_split_abstained_agent_responses():
    from augur.personas.base import AgentResponse, SignalType

    def resp(meta):
        r = AgentResponse(agent_id="x", agent_name="X", signal=SignalType.NEUTRAL,
                          confidence=0.0, score=5.0, reasoning="")
        r.metadata.update(meta)
        return r

    no_rules, no_data = split_abstained({
        "dalio": resp({}),
        "buffett": resp({"not_applicable": True, "reason": "fund"}),
        "marks": resp({"not_applicable": True, "reason": "fund_data_missing"}),
    })
    assert no_rules == ["buffett"] and no_data == ["marks"]


def test_disagreement_summary_splits_reasons():
    from augur.disagreement import build_disagreement_from_bundle

    dm = build_disagreement_from_bundle(_mixed_bundle(), "SPY", "run_SPY_x")
    assert dm.consensus_strength == "n/a"
    assert "17 abstained" in dm.summary
    assert "14 rules not applicable to funds" in dm.summary
    assert "3 fund technicals missing: arps, marks, soros" in dm.summary


def test_report_from_run_splits_reasons(monkeypatch):
    import augur.run_tracker as rt

    monkeypatch.setattr(rt, "latest_run_id", lambda *a, **k: "run_SPY_x")
    monkeypatch.setattr(rt, "load_run_bundle_dict", lambda run_id: _mixed_bundle())
    result = CliRunner().invoke(main, ["report", "from-run", "SPY"])
    assert result.exit_code == 0, result.output
    assert "3 fund technicals missing: arps, marks, soros" in result.output
    assert "14 rules not applicable to funds" in result.output


def test_mcp_fund_text_splits_reasons():
    from augur.mcp_server import _fund_consensus_text
    from augur.registry import AgentRegistry, DecisionCoordinator

    ctx = spy_ctx_no_technicals()
    with patch("augur.registry._get_learning_engine") as le, \
         patch("augur.registry._check_and_record_outcomes"):
        le.return_value.has_learned_weights = False
        coord = DecisionCoordinator(AgentRegistry())
        results = coord.analyze_with_all(ctx)
        consensus = coord.get_consensus(results, ticker="SPY", context=ctx)
    text = _fund_consensus_text("SPY", ctx, results, consensus, "yfinance", "fresh")
    assert "Signal: WITHHELD" in text
    assert "3 abstained because fund technicals are missing" in text
    assert "Abstained (3, fund technicals missing): arps, marks, soros" in text
    assert "Abstained (14, rules not applicable to funds)" in text


def test_skill_personas_step_records_abstention():
    from augur.personas.base import AgentResponse, SignalType
    from augur.skills import handlers

    def resp(aid, meta):
        r = AgentResponse(agent_id=aid, agent_name=aid, signal=SignalType.NEUTRAL,
                          confidence=0.0, score=5.0, reasoning="")
        r.metadata.update(meta)
        return r

    responses = {"dalio": resp("dalio", {}),
                 "marks": resp("marks", {"not_applicable": True, "reason": "fund_data_missing"})}
    with patch("augur.registry.DecisionCoordinator") as dc:
        dc.return_value.analyze_with_all.return_value = responses
        dc.return_value.get_consensus.return_value = resp("consensus", {})
        out = handlers.analyze_personas({"ticker": "spy"}, {"collect": {"_ctx": object()}})
    assert "abstained" not in out["personas"]["dalio"]
    assert out["personas"]["marks"]["abstain_reason"] == "fund_data_missing"


# --------------------------------------------------------------------------
# Dividend yield (live yfinance 1.7 info dicts, 2026-11-26)
# --------------------------------------------------------------------------

SPY = {"dividendRate": None, "dividendYield": 1.0, "trailingAnnualDividendRate": 5.662,
       "trailingAnnualDividendYield": 0.007877236, "yield": 0.01}
QQQ = {"dividendRate": None, "dividendYield": 0.45, "trailingAnnualDividendRate": 1.77,
       "trailingAnnualDividendYield": 0.00277386, "yield": 0.0045}
AAPL = {"dividendRate": 1.08, "dividendYield": 0.3, "trailingAnnualDividendRate": 1.06,
        "trailingAnnualDividendYield": 0.002993758}
KO = {"dividendRate": 2.12, "dividendYield": 2.17, "trailingAnnualDividendRate": 2.1,
      "trailingAnnualDividendYield": 0.021511983}
TENCENT = {"dividendRate": 5.3, "dividendYield": 1.57, "trailingAnnualDividendRate": 4.763,
           "trailingAnnualDividendYield": 0.014116775}


@pytest.mark.parametrize("info,price,expected", [
    (SPY, 716.70, 0.0100),       # read 1.0 (100%) before 14.1; = ETF profile yield
    (QQQ, 633.93, 0.0045),
    (AAPL, 355.58, 0.0030),
    (KO, 97.59, 0.0217),
    (TENCENT, 341.0, 0.0155),
])
def test_dividend_yield_live_shapes(info, price, expected):
    assert dividend_yield_from_info(info, price) == pytest.approx(expected, abs=2e-4)


def test_dividend_yield_equity_without_rate_is_not_read_as_fraction():
    # Only the ambiguous percent field: 0.3 means 0.3%, not 30%.
    assert dividend_yield_from_info({"dividendYield": 0.3}, 100.0) == pytest.approx(0.003)
    assert dividend_yield_from_info({"dividendYield": 2.17}, 100.0) == pytest.approx(0.0217)
    assert dividend_yield_from_info({"trailingAnnualDividendRate": 2.0}, 100.0) == pytest.approx(0.02)
    assert dividend_yield_from_info({"yield": 0.012}, 0.0) == pytest.approx(0.012)
    assert dividend_yield_from_info({}, 100.0) == 0.0


# --------------------------------------------------------------------------
# `augur watchlist watch`: no alert on a placeholder 5.0
# --------------------------------------------------------------------------

def _watch_once(ctx_factory, args):
    import augur.cli_commands.monitor as monitor

    def stop(_):
        raise KeyboardInterrupt

    with patch.object(monitor, "_auto_fetch_context", lambda t: ctx_factory()), \
         patch("time.sleep", stop), \
         patch("augur.registry._get_learning_engine") as le, \
         patch("augur.registry._check_and_record_outcomes"):
        le.return_value.has_learned_weights = False
        return CliRunner().invoke(main, ["watchlist", "watch", "SPY", *args])


def test_watch_withheld_fund_does_not_alert():
    result = _watch_once(spy_ctx_no_technicals, ["--alert-above", "3"])
    assert "WITHHELD" in result.output, result.output
    assert "ALERT" not in result.output
    assert "5.0/10" not in result.output


def test_watch_abstaining_persona_does_not_alert():
    result = _watch_once(spy_ctx_no_technicals, ["--persona", "buffett", "--alert-above", "3"])
    assert "N/A" in result.output, result.output
    assert "ALERT" not in result.output


def test_watch_real_fund_consensus_can_alert():
    from tests.test_etf_output import spy_ctx

    result = _watch_once(spy_ctx, ["--alert-above", "0.5"])
    assert "WITHHELD" not in result.output, result.output
    assert "ALERT: score" in result.output


# --------------------------------------------------------------------------
# Dashboard stock page: a real fund consensus is labelled, no Kelly size
# --------------------------------------------------------------------------

def test_stock_page_labels_fund_consensus_without_kelly():
    import re
    from pathlib import Path

    import augur

    root = Path(augur.__file__).parent.parent / "dashboard"
    html = (root / "templates" / "stocks.html").read_text(encoding="utf-8")
    assert "function isFundConsensus(cons)" in html
    assert "cons.metadata.fund_basis" in html
    assert "if (fundCons) posPct = 'n/a'" in html
    assert "_fundConsensusMessage(ticker, cons)" in html
    i18n = (root / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    for key in ("fund-consensus-label", "fund-consensus-tip", "fund-consensus-oracle"):
        assert len(re.findall(rf'"{key}":', i18n)) == 4, key  # zh / en / ja / ko


def test_cli_consensus_withheld_sentence_names_missing_technicals():
    from tests.test_etf_output import _run

    with patch("augur.data.fetch_market_context", side_effect=lambda *a, **k: spy_ctx_no_technicals()), \
         patch("augur.optional_deps.is_available", return_value=True), \
         patch("augur.registry._get_learning_engine") as le, \
         patch("augur.registry._check_and_record_outcomes"):
        le.return_value.has_learned_weights = False
        out = _run(["consensus", "SPY"]).output
    assert "personas gave a fund reading (at least 3 are needed)" in out, out
    assert "abstained because fund technicals are missing" in out
    assert "have rules that apply to a fund" not in out
