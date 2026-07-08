# -*- coding: utf-8 -*-
"""Tests for the single-agent factor breakdown (stocks.html) and the shared
factor-map.js module it extracted out of compare.html.

This feature has no Python backend route — the data (metadata.factors) is
already served verbatim by /api/analyze/{ticker}, and everything else is
client-side categorization/rendering. So coverage here is: (1) the shared
JS module is actually wired into both pages that need it, (2) the expected
DOM hooks exist in stocks.html for the render function to attach to, and
(3) the categorization/inversion logic in factor-map.js is behaviorally
correct — executed for real via Node (skipped if Node isn't on PATH,
matching this repo's optional-tool convention, e.g. ruff in the Makefile).
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app

REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = REPO_ROOT / "src" / "dashboard" / "static"
TEMPLATES_DIR = REPO_ROOT / "src" / "dashboard" / "templates"
FACTOR_MAP_JS = STATIC_DIR / "js" / "factor-map.js"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestFactorMapModuleWiring:
    """Both compare.html and stocks.html must load the shared module, and
    neither should carry its own duplicate copy of the mapping table."""

    def test_factor_map_js_file_exists(self):
        assert FACTOR_MAP_JS.is_file()

    def test_factor_map_js_served_over_http(self, client):
        resp = client.get("/static/js/factor-map.js")
        assert resp.status_code == 200
        assert "AugurFactorMap" in resp.text

    @pytest.mark.parametrize("template", ["compare.html", "stocks.html"])
    def test_template_includes_factor_map_script(self, template):
        html = (TEMPLATES_DIR / template).read_text(encoding="utf-8")
        assert '/static/js/factor-map.js' in html

    def test_compare_html_has_no_duplicate_factor_map_literal(self):
        """compare.html was refactored to consume AugurFactorMap.FACTOR_MAP
        instead of defining its own copy — regression guard against the
        ~70-key table silently drifting back into two places."""
        html = (TEMPLATES_DIR / "compare.html").read_text(encoding="utf-8")
        assert "AugurFactorMap.FACTOR_MAP" in html
        # The old inline literal started with this exact key ordering; its
        # absence here means it wasn't accidentally re-duplicated.
        assert "'valuation_acceptability','relative_valuation'" not in html.replace(" ", "")


class TestStocksHtmlFactorModalDom:
    """stocks.html must have the DOM hooks renderAgentFactors() attaches to."""

    @pytest.fixture(scope="class")
    def html(self):
        return (TEMPLATES_DIR / "stocks.html").read_text(encoding="utf-8")

    @pytest.mark.parametrize("element_id", [
        "agd-factors", "agd-factors-cats", "agd-factors-list",
    ])
    def test_modal_has_factor_elements(self, html, element_id):
        assert f'id="{element_id}"' in html

    def test_render_function_defined(self, html):
        assert "function renderAgentFactors(agent)" in html

    def test_show_agent_detail_calls_render_factors(self, html):
        """renderAgentFactors must actually be invoked from showAgentDetail,
        not just defined and orphaned."""
        show_fn_start = html.index("function showAgentDetail(agent)")
        show_fn_body = html[show_fn_start:show_fn_start + 1500]
        assert "renderAgentFactors(agent)" in show_fn_body

    def test_expand_factors_i18n_key_present(self, html):
        assert 'data-i18n="stocks-expand-factors"' in html


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
class TestFactorMapJsBehavior:
    """Executes the real factor-map.js in Node to verify the categorization
    and safety-inversion logic, not just that the file is well-formed."""

    def _run(self, js_snippet: str):
        script = f"""
        global.window = {{}};
        {FACTOR_MAP_JS.read_text(encoding='utf-8')}
        var AugurFactorMap = window.AugurFactorMap;
        {js_snippet}
        """
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, f"node exited non-zero: {result.stderr}"
        return result.stdout.strip()

    def test_categories_list(self):
        out = self._run("console.log(JSON.stringify(AugurFactorMap.CATEGORIES));")
        assert json.loads(out) == ["valuation", "growth", "quality", "momentum", "safety"]

    def test_cat_avg_averages_matching_keys(self):
        out = self._run(
            "console.log(AugurFactorMap.catAvg({moat: 8, valuation: 6, growth: 7}, 'quality'));"
        )
        assert float(out) == pytest.approx(8.0)

    def test_cat_avg_returns_null_when_no_keys_match(self):
        out = self._run(
            "console.log(AugurFactorMap.catAvg({unrelated_key: 5}, 'valuation'));"
        )
        assert out == "null"

    def test_safety_inversion_flips_risk_factors(self):
        """tech_risk=8 (high risk) must invert to a safety score of 2 (low safety)."""
        out = self._run("console.log(AugurFactorMap.catAvg({tech_risk: 8}, 'safety'));")
        assert float(out) == pytest.approx(2.0)

    def test_insider_buying_signal_registered_under_quality(self):
        """Phase C (EDGAR Form 4) factor must be wired into the radar's
        category mapping, not just computed and silently unused by the UI."""
        out = self._run("console.log(AugurFactorMap.FACTOR_MAP.quality.includes('insider_buying_signal'));")
        assert out == "true"

    def test_insider_buying_signal_contributes_to_quality_average(self):
        out = self._run(
            "console.log(AugurFactorMap.catAvg({insider_buying_signal: 8}, 'quality'));"
        )
        assert float(out) == pytest.approx(8.0)

    def test_safety_inversion_averages_with_non_inverted_keys(self):
        """Regression test: debt_safety=8 (already safety-direction, not
        inverted) and tech_risk=8 (inverted to 2) sharing the *same raw
        value* used to collide in a value-based dedup check and silently
        drop tech_risk from the average entirely (catAvg returned 8.0
        instead of the correct (8+2)/2=5.0). The dedup now tracks factor
        *keys*, not numeric values."""
        out = self._run(
            "console.log(AugurFactorMap.catAvg({debt_safety: 8, tech_risk: 8}, 'safety'));"
        )
        assert float(out) == pytest.approx(5.0)

    def test_has_factors_threshold(self):
        below = self._run("console.log(AugurFactorMap.hasFactors({a:1,b:2}));")
        at = self._run("console.log(AugurFactorMap.hasFactors({a:1,b:2,c:3}));")
        assert below == "false"
        assert at == "true"

    def test_has_factors_handles_null(self):
        out = self._run("console.log(AugurFactorMap.hasFactors(null));")
        assert out == "false"
