# -*- coding: utf-8 -*-
"""v14 dashboard checks: version strings and the ETF overview card."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

import augur
from dashboard.app import app

DASH = Path(__file__).resolve().parents[1] / "src" / "dashboard"
client = TestClient(app)


class TestVersionStrings:
    def test_health_reports_package_version(self):
        data = client.get("/api/health").json()
        assert data["version"] == augur.__version__

    def test_openapi_reports_package_version(self):
        assert app.version == augur.__version__

    def test_no_hardcoded_versions_in_dashboard(self):
        pat = re.compile(r"""(?:"version":\s*"|version="|\?v=|Augur v)\d+\.\d+\.\d+""")
        hits = []
        for p in DASH.rglob("*"):
            if p.suffix in (".py", ".html") and p.is_file():
                for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if pat.search(line):
                        hits.append(f"{p.relative_to(DASH)}:{i}")
        assert hits == []

    def test_base_template_renders_version(self):
        html = client.get("/").text
        assert f"?v={augur.__version__}" in html


# ---------------------------------------------------------------------------
# ETF overview card
# ---------------------------------------------------------------------------
import json  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402

from augur.personas.base import MarketContext  # noqa: E402
from dashboard.etf_overview import build_etf_overview  # noqa: E402

ETF_JS = DASH / "static" / "js" / "etf-card.js"

ETF_PROFILE = {
    "aum_usd_bn": 512.3,
    "expense_ratio": 0.0009,
    "premium_pct": -0.04,
    "nav": 601.12,
    "nav_date": "2026-11-25",
    "nav_date_inferred": True,
    "top10_weight": 0.371,
    "category": "Large Blend <b>",
    "spread_pct": 0.002,
    "source": "yfinance",
}


def _etf_ctx():
    return MarketContext(ticker="SPY", price=600.9, asset_type="etf", etf=dict(ETF_PROFILE))


def _equity_ctx():
    return MarketContext(ticker="AAPL", price=200.0, pe=30.0)


class TestEtfOverviewPayload:
    def test_fund_payload_passes_contract_keys(self):
        ov = build_etf_overview(_etf_ctx())
        assert ov["asset_type"] == "etf"
        assert ov["aum_usd_bn"] == 512.3
        assert ov["expense_ratio"] == 0.0009
        assert ov["nav_date"] == "2026-11-25" and ov["nav_date_inferred"] is True
        assert ov["category"] == "Large Blend <b>"

    def test_missing_keys_are_none_not_zero(self):
        ov = build_etf_overview(MarketContext(ticker="X", asset_type="etf", etf={"aum_usd_bn": "n/a"}))
        assert ov["aum_usd_bn"] is None
        assert ov["expense_ratio"] is None and ov["category"] is None
        assert ov["nav_date_inferred"] is False

    def test_equity_has_no_payload(self):
        assert build_etf_overview(_equity_ctx()) is None

    @pytest.mark.parametrize("ctx_factory,is_etf", [(_etf_ctx, True), (_equity_ctx, False)])
    def test_analyze_api_carries_payload(self, monkeypatch, ctx_factory, is_etf):
        import augur.data as data_mod
        import dashboard.routes.analysis as analysis_routes

        monkeypatch.setattr(data_mod, "fetch_market_context", lambda t, *a, **k: ctx_factory())
        monkeypatch.setattr(analysis_routes, "_check_rate_limit", lambda t: True)
        monkeypatch.setattr(analysis_routes, "_build_api_provenance", lambda *a, **k: None)
        ticker = "SPY" if is_etf else "AAPL"
        data = client.get(f"/api/analyze/{ticker}").json()
        assert data["market_data"]["asset_type"] == ("etf" if is_etf else "equity")
        if is_etf:
            assert data["etf_overview"]["aum_usd_bn"] == 512.3
        else:
            assert data["etf_overview"] is None

    def test_stock_page_wires_card(self):
        html = client.get("/stocks").text
        assert 'id="etf-card"' in html
        assert f"/static/js/etf-card.js?v={augur.__version__}" in html
        assert "renderEtfCard(" in html


def _render_card(payload):
    script = (
        "const window = {};"
        f"eval(require('fs').readFileSync({json.dumps(str(ETF_JS))}, 'utf8'));"
        f"process.stdout.write(window.buildEtfCardHtml({json.dumps(payload)}));"
    )
    return subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
class TestEtfCardRender:
    def test_renders_fund_card(self):
        html = _render_card(build_etf_overview(_etf_ctx()))
        assert "ETF Overview" in html
        assert "$512B" in html             # aum_usd_bn
        assert "0.09%" in html             # 0.0009 decimal -> percent
        assert "-0.04%" in html            # premium_pct already percent
        assert "2026-11-25" in html and "(date inferred)" in html
        assert "37.1%" in html             # top10_weight decimal -> percent
        assert "0.002%" in html            # spread_pct
        assert "Large Blend &lt;b&gt;" in html and "<b>" not in html

    def test_unknown_values_show_dashes(self):
        html = _render_card(build_etf_overview(MarketContext(ticker="X", asset_type="etf")))
        assert "ETF Overview" in html and "--" in html
        assert "inferred" not in html

    def test_equity_renders_nothing(self):
        assert _render_card(build_etf_overview(_equity_ctx())) == ""


# ---------------------------------------------------------------------------
# Committee verdict for a fund
# ---------------------------------------------------------------------------
class TestCommitteeFundVerdict:
    def _run(self, monkeypatch):
        import augur.data as data_mod

        monkeypatch.setattr(data_mod, "fetch_market_context", lambda t, *a, **k: _etf_ctx())
        return client.post("/api/committee", json={"ticker": "SPY", "question": "q"}).json()

    def test_withheld_verdict_and_abstainers(self, monkeypatch):
        data = self._run(monkeypatch)
        v = data["verdict"]
        assert v["withheld"] is True
        assert v["abstained_count"] > 0
        assert v["applicable_count"] + v["abstained_count"] == len(data["opinions"])
        # abstainers are not counted as neutral votes
        assert v["vote"]["abstained"] == v["abstained_count"]
        assert sum(v["vote"][k] for k in ("bullish", "neutral", "bearish")) == v["applicable_count"]
        assert v["kelly_pct"] == 0

    def test_abstainers_flagged_and_sorted_last(self, monkeypatch):
        ops = self._run(monkeypatch)["opinions"]
        flags = [op["not_applicable"] for op in ops]
        assert any(flags) and flags == sorted(flags)

    def test_page_renders_withheld_state(self):
        html = client.get("/committee").text
        assert "v.withheld" in html and "op.not_applicable" in html
        assert 'data-i18n="committee-question-ph"' in html


class TestStockPageFundPolish:
    def test_analyze_api_reports_currency_and_name(self, monkeypatch):
        import augur.data as data_mod
        import dashboard.routes.analysis as analysis_routes

        ctx = MarketContext(ticker="510300.SS", price=3.96, asset_type="etf", currency="CNY",
                            company_name="CSI 300 ETF", etf={"nav": 3.97})
        monkeypatch.setattr(data_mod, "fetch_market_context", lambda t, *a, **k: ctx)
        monkeypatch.setattr(analysis_routes, "_check_rate_limit", lambda t: True)
        monkeypatch.setattr(analysis_routes, "_build_api_provenance", lambda *a, **k: None)
        data = client.get("/api/analyze/510300.SS").json()
        assert data["market_data"]["currency"] == "CNY"
        assert data["market_data"]["company_name"] == "CSI 300 ETF"
        assert data["etf_overview"]["currency"] == "CNY"

    def test_withheld_oracle_does_not_echo_engine_reasoning(self):
        html = client.get("/stocks").text
        assert "_withheldMessage(ticker, cons)" in html
        assert "too few personas have rules that apply to this fund, so no signal or position size is given. <br><br>' + escapeHtml(cons.reasoning" not in html
        assert "点击查看详情" not in html


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
class TestEtfCardPolish:
    def test_nav_value_shown_with_currency(self):
        ov = build_etf_overview(MarketContext(ticker="SPY", asset_type="etf", currency="USD", etf=dict(ETF_PROFILE)))
        html = _render_card(ov)
        assert "601.12 USD" in html and "2026-11-25" in html

    def test_unknown_values_are_muted(self):
        html = _render_card(build_etf_overview(MarketContext(ticker="X", asset_type="etf")))
        assert "etf-card__value--na" in html


class TestFundReportRoutes:
    def _analysis(self, monkeypatch):
        import augur.data as data_mod
        import dashboard.routes.analysis as analysis_routes

        ctx = MarketContext(ticker="SPY", price=600.9, asset_type="etf", currency="USD",
                            company_name="SPDR S&P 500 ETF Trust", etf=dict(ETF_PROFILE))
        monkeypatch.setattr(data_mod, "fetch_market_context", lambda t, *a, **k: ctx)
        monkeypatch.setattr(analysis_routes, "_check_rate_limit", lambda t: True)
        monkeypatch.setattr(analysis_routes, "_build_api_provenance", lambda *a, **k: None)
        return client.get("/api/analyze/SPY").json()

    def test_post_report_keeps_fund_profile(self, monkeypatch):
        data = self._analysis(monkeypatch)
        out = client.post("/api/report/SPY", json=data).json()
        assert out["consensus_withheld"] is True
        report = out["report"]
        assert "（EQUITY）" not in report and "（ETF）" in report
        assert "$512" in report and "0.09%" in report      # AUM and expense ratio reached the report
        assert "SPDR S&P 500 ETF Trust" in report

    def test_get_report_flags_withheld(self, monkeypatch):
        self._analysis(monkeypatch)
        out = client.get("/api/report/SPY?auto_fetch=true").json()
        assert out["consensus_withheld"] is True

    def test_report_page_handles_withheld(self):
        html = client.get("/report/SPY").text
        assert "data.consensus_withheld" in html
