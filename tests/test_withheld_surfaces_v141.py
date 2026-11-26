# -*- coding: utf-8 -*-
"""v14.1: no surface shows a withheld fund consensus as a neutral 5.0.

Every test builds the consensus by hand. The withheld case deliberately
uses an *equity*-typed context and the real-score case a *fund*-typed one,
so the surfaces are shown to key off ``metadata.consensus_withheld`` and
never off the asset type. No network: the data layer and coordinator are
replaced with fakes.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from augur.consensus_display import (
    WITHHELD_SIGNAL,
    consensus_record,
    consensus_withheld,
    display_confidence,
    display_persona_score,
    display_score,
    display_signal,
)
from augur.personas.base import AgentResponse, MarketContext, SignalType

DASH = Path(__file__).resolve().parents[1] / "src" / "dashboard"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _persona(aid, signal=SignalType.NEUTRAL, score=5.0, abstained=False):
    meta = {"not_applicable": True} if abstained else {}
    return AgentResponse(agent_id=aid, agent_name=aid.title(), signal=signal,
                         confidence=0.5 if not abstained else 0.0, score=score,
                         reasoning="r", metadata=meta)


def withheld_consensus():
    return AgentResponse(
        agent_id="consensus", agent_name="Multi-Agent Consensus",
        signal=SignalType.NEUTRAL, confidence=0.0, score=5.0,
        reasoning="too few apply", key_findings=["f1"],
        metadata={"consensus_withheld": True, "withheld_reason": "only 1 of 3 apply",
                  "position_sizing": {"position_pct": 0.0}, "position_pct": 0.0},
    )


def real_consensus():
    return AgentResponse(
        agent_id="consensus", agent_name="Multi-Agent Consensus",
        signal=SignalType.BULLISH, confidence=0.62, score=7.4,
        reasoning="real", key_findings=["f1"],
        metadata={"position_sizing": {"position_pct": 2.5}},
    )


def withheld_responses():
    return {
        "dalio": _persona("dalio", SignalType.BULLISH, 6.8),
        "buffett": _persona("buffett", abstained=True),
        "graham": _persona("graham", abstained=True),
    }


def real_responses():
    return {
        "dalio": _persona("dalio", SignalType.BULLISH, 6.8),
        "marks": _persona("marks", SignalType.BULLISH, 7.9),
        "soros": _persona("soros", SignalType.NEUTRAL, 5.6),
    }


def equity_ctx(ticker="AAPL"):
    return MarketContext(ticker=ticker, price=210.0, asset_type="equity")


def fund_ctx(ticker="SPY"):
    return MarketContext(ticker=ticker, price=600.0, asset_type="etf")


class FakeCoordinator:
    """Returns a fixed consensus per ticker; records nothing, fetches nothing."""

    def __init__(self, plan):
        self.plan = plan  # ticker -> (responses, consensus)

    def analyze_with_all(self, ctx, enabled_personas=None, **_kw):
        return self.plan[ctx.ticker.upper()][0]

    def get_consensus(self, results, ticker=None, context=None, **_kw):
        return self.plan[(ticker or context.ticker).upper()][1]

    def run_debate(self, ctx, rounds=2, **_kw):
        return self.plan[ctx.ticker.upper()][0]


PLAN = {
    # Equity-typed but withheld: must render WITHHELD.
    "AAPL": (withheld_responses(), withheld_consensus()),
    # Fund-typed but real: must render its score.
    "SPY": (real_responses(), real_consensus()),
}
CTX = {"AAPL": equity_ctx, "SPY": fund_ctx}


@pytest.fixture
def fake_data(monkeypatch):
    import augur.data

    monkeypatch.setattr(augur.data, "fetch_market_context",
                        lambda t, *a, **k: CTX[t.upper()](t.upper()))


@pytest.fixture
def history_dir(tmp_path, monkeypatch):
    import augur.history as h

    monkeypatch.setattr(h, "HISTORY_DIR", tmp_path / "history")
    h._invalidate_count_cache()
    return h


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

class TestHelper:
    def test_reads_every_flag_spelling(self):
        assert consensus_withheld(withheld_consensus())
        assert consensus_withheld(withheld_consensus().to_dict())
        assert consensus_withheld({"signal": "neutral", "consensus_withheld": True})
        assert consensus_withheld({"signal": "neutral", "withheld": True})
        assert not consensus_withheld(real_consensus())
        assert not consensus_withheld({"signal": "neutral", "score": 5.0})
        assert not consensus_withheld(None)

    def test_display(self):
        w, r = withheld_consensus(), real_consensus()
        assert display_signal(w) == WITHHELD_SIGNAL == "WITHHELD (fund)"
        assert display_score(w) == "--" and display_confidence(w) == "--"
        assert display_signal(r) == "BULLISH"
        assert display_signal(r, {"bullish": "看多"}) == "看多"
        assert display_score(r) == "7.4/10" and display_confidence(r) == "62%"

    def test_record_keeps_flag(self):
        rec = consensus_record(withheld_consensus())
        assert rec["consensus_withheld"] is True
        assert rec["withheld_reason"] == "only 1 of 3 apply"
        assert "consensus_withheld" not in consensus_record(real_consensus())

    def test_persona_score(self):
        assert display_persona_score(_persona("graham", abstained=True)) == "N/A"
        assert display_persona_score(_persona("dalio", score=6.8)) == "6.8/10"


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------

class TestHistory:
    def test_withheld_flag_round_trips(self, history_dir):
        history_dir.save_analysis("AAPL", {"consensus": consensus_record(withheld_consensus())})
        history_dir.save_analysis("SPY", {"consensus": consensus_record(real_consensus())})
        recs = {r["ticker"]: r for r in history_dir.list_history()}
        assert recs["AAPL"]["consensus_withheld"] is True
        assert "consensus_withheld" not in recs["SPY"]
        assert recs["SPY"]["score"] == 7.4

    def test_v14_full_to_dict_records_are_detected(self, history_dir):
        # /ws/analyze stores consensus.to_dict(): the flag sits in metadata.
        history_dir.save_analysis("AAPL", {"consensus": withheld_consensus().to_dict()})
        assert history_dir.list_history()[0]["consensus_withheld"] is True

    def test_withheld_is_not_neutral(self, history_dir):
        history_dir.save_analysis("AAPL", {"consensus": consensus_record(withheld_consensus())})
        history_dir.save_analysis("MSFT", {"consensus": {"signal": "neutral", "score": 5.2}})
        neutral = history_dir.list_history(signal_filter="neutral")
        assert [r["ticker"] for r in neutral] == ["MSFT"]
        assert history_dir.count_history(signal_filter="neutral") == 1


# ---------------------------------------------------------------------------
# augur cron
# ---------------------------------------------------------------------------

class TestCron:
    def test_watchlist_run_saves_flag_and_prints_withheld(self, monkeypatch, history_dir,
                                                         fake_data, capsys):
        import augur.cron as cron
        import augur.registry as registry

        monkeypatch.setattr(cron, "load_watchlist",
                            lambda: {"watchlist": [{"ticker": "AAPL"}, {"ticker": "SPY"}]})
        monkeypatch.setattr(cron, "_send_notifications", lambda *a, **k: None)
        monkeypatch.setattr(cron, "_WATCHLIST_FETCH_DELAY_SECONDS", 0)
        monkeypatch.setattr(registry, "DecisionCoordinator", lambda reg: FakeCoordinator(PLAN))
        monkeypatch.setattr(registry, "resolve_pending_outcomes", lambda *a, **k: {}, raising=False)

        results = cron.run_watchlist_analysis()
        out = capsys.readouterr().out
        assert "AAPL: WITHHELD (fund) (--)" in out
        assert "SPY: BULLISH (7.4/10)" in out
        msg = {r["ticker"]: r["message"] for r in results}
        assert "WITHHELD (FUND)" in msg["AAPL"] and "5.0/10" not in msg["AAPL"].split("Agent")[0]
        assert "7.4/10" in msg["SPY"]
        recs = {r["ticker"]: r for r in history_dir.list_history()}
        assert recs["AAPL"]["consensus_withheld"] is True
        assert "consensus_withheld" not in recs["SPY"]

    @pytest.mark.parametrize("threshold,expected", [(3, ["SPY"]), (0, ["AAPL", "SPY"])])
    def test_notifications_skip_withheld_when_thresholded(self, monkeypatch, threshold, expected):
        import augur.cron as cron

        sent = []
        monkeypatch.setattr(cron, "_send_telegram_notifications",
                            lambda cfg, results, th: sent.extend(r["ticker"] for r in results))
        config = {"notifications": {"alert_threshold": threshold,
                                    "telegram": {"enabled": True, "chat_id": "1", "token": "t"}}}
        cron._send_notifications(config, [
            {"ticker": "AAPL", "consensus": withheld_consensus(), "message": ""},
            {"ticker": "SPY", "consensus": real_consensus(), "message": ""},
        ])
        assert sent == expected


# ---------------------------------------------------------------------------
# Chat bots
# ---------------------------------------------------------------------------

def _bot_texts(consensus, responses):
    from augur.bots import lark_bot, slack_bot, telegram_bot, wechat_bot

    return {
        "telegram": telegram_bot.format_consensus_message("AAPL", consensus, responses),
        "slack_blocks": json.dumps(slack_bot.format_consensus_blocks("AAPL", consensus, responses),
                                   ensure_ascii=False),
        "slack_text": slack_bot.format_consensus_text("AAPL", consensus, responses),
        "lark_card": json.dumps(lark_bot.format_lark_card("AAPL", consensus, responses),
                                ensure_ascii=False),
        "lark_post": json.dumps(lark_bot.format_lark_rich_text("AAPL", consensus, responses),
                                ensure_ascii=False),
        "wechat": wechat_bot.format_wechat_message("AAPL", consensus, responses),
    }


class TestBots:
    def test_withheld(self):
        for name, text in _bot_texts(withheld_consensus(), withheld_responses()).items():
            assert "WITHHELD" in text.upper(), name
            assert "5.0/10" not in text, name   # neither consensus nor abstainers
            assert "N/A" in text, name           # abstaining personas
            assert "6.8" in text, name           # the one applicable persona still shows

    def test_real_fund_consensus_shows_score(self):
        for name, text in _bot_texts(real_consensus(), real_responses()).items():
            assert "WITHHELD" not in text.upper(), name
            assert "7.4/10" in text, name

    def test_single_persona_messages_mark_abstainers(self):
        from augur.bots import lark_bot, slack_bot, telegram_bot, wechat_bot

        r = _persona("graham", abstained=True)
        texts = [telegram_bot.format_single_agent_message("SPY", r),
                 json.dumps(slack_bot.format_single_agent_blocks("SPY", r), ensure_ascii=False),
                 wechat_bot.format_single_agent_wechat("SPY", r)
                 if hasattr(wechat_bot, "format_single_agent_wechat") else None]
        for text in filter(None, texts):
            assert "N/A" in text and "5.0/10" not in text

    def test_lark_card_is_grey_when_withheld(self):
        from augur.bots import lark_bot

        card = lark_bot.format_lark_card("AAPL", withheld_consensus(), withheld_responses())
        assert card["header"]["template"] == "grey"


# ---------------------------------------------------------------------------
# Built-in skill handlers
# ---------------------------------------------------------------------------

class TestSkillHandlers:
    def test_analyze_personas_carries_flag(self, monkeypatch):
        import augur.registry as registry
        from augur.skills import handlers

        monkeypatch.setattr(registry, "DecisionCoordinator", lambda reg: FakeCoordinator(PLAN))
        out = handlers.analyze_personas({"ticker": "aapl"}, {"s": {"_ctx": equity_ctx()}})
        assert out["consensus"]["consensus_withheld"] is True
        assert out["consensus"]["kelly_pct"] == 0.0
        out = handlers.analyze_personas({"ticker": "spy"}, {"s": {"_ctx": fund_ctx()}})
        assert "consensus_withheld" not in out["consensus"]
        assert out["consensus"]["score"] == 7.4

    def test_compare_skips_placeholder_score_diff(self, monkeypatch):
        import augur.run_tracker as rt
        from augur.skills import handlers

        monkeypatch.setattr(rt, "latest_run_id", lambda *a, **k: "run_prev")
        monkeypatch.setattr(rt, "load_run_bundle_dict", lambda rid: {"created_at": "x"})
        monkeypatch.setattr(rt, "extract_persona_results", lambda b: (
            {}, {"signal": "bullish", "score": 7.4}))
        upstream = {"s": {"personas": {}, "consensus": consensus_record(withheld_consensus())}}
        diffs = handlers.compare_with_previous_run({"ticker": "AAPL"}, upstream)["diffs"]
        assert diffs == [{"field": "consensus.signal", "before": "bullish", "after": "withheld"}]

    def test_dossier_says_withheld(self):
        from augur.skills import handlers

        upstream = {"s": {"personas": {}, "evidence_items": [], "diffs": [], "event": {},
                          "consensus": consensus_record(withheld_consensus())}}
        text = json.dumps(handlers.build_earnings_dossier(
            {"ticker": "AAPL", "as_of": "2026-11-26", "event_id": "e"}, upstream), ensure_ascii=False)
        assert "WITHHELD (fund), score --" in text
        assert "5.0/10" not in text


# ---------------------------------------------------------------------------
# Dashboard routes
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from dashboard.app import app

    return TestClient(app)


class TestDashboardRoutes:
    def test_scanner_flags_withheld(self, client, monkeypatch, fake_data):
        import dashboard.routes.analysis as analysis

        monkeypatch.setattr(analysis, "get_coordinator", lambda: FakeCoordinator(PLAN))
        rows = {r["ticker"]: r for r in
                client.post("/api/scanner/run", json={"tickers": ["AAPL", "SPY"]}).json()["results"]}
        assert rows["AAPL"]["consensus_withheld"] is True
        assert {a["agent_id"]: a["not_applicable"] for a in rows["AAPL"]["agents"]}["graham"] is True
        assert rows["SPY"]["consensus_withheld"] is False
        assert rows["SPY"]["consensus_score"] == 7.4

    def test_watchlist_run(self, client, monkeypatch, fake_data, history_dir):
        import augur.cron as cron
        import dashboard.routes.watchlist as wl

        saved = {}
        monkeypatch.setattr(cron, "load_watchlist",
                            lambda: {"watchlist": [{"ticker": "AAPL"}, {"ticker": "SPY"}]})
        monkeypatch.setattr(cron, "save_watchlist", lambda cfg: saved.update(cfg))
        monkeypatch.setattr(wl, "get_coordinator", lambda: FakeCoordinator(PLAN))
        rows = {r["ticker"]: r for r in client.post("/api/watchlist/run").json()["results"]}
        aapl, spy = rows["AAPL"], rows["SPY"]
        assert aapl["consensus_withheld"] is True and aapl["kelly_pct"] == 0.0
        # Abstainers are not HOLD votes.
        assert (aapl["buy_count"], aapl["hold_count"], aapl["abstained_count"]) == (1, 0, 2)
        assert spy["consensus_withheld"] is False and spy["score"] == 7.4
        items = {w["ticker"]: w for w in saved["watchlist"]}
        assert items["AAPL"]["last_withheld"] is True
        assert "last_withheld" not in items["SPY"]
        recs = {r["ticker"]: r for r in history_dir.list_history()}
        assert recs["AAPL"]["consensus_withheld"] is True
        assert "consensus_withheld" not in recs["SPY"]

    def test_cron_run_now(self, client, monkeypatch):
        import augur.cron as cron

        monkeypatch.setattr(cron, "run_watchlist_analysis", lambda: [
            {"ticker": "AAPL", "consensus": withheld_consensus(), "message": "m"},
            {"ticker": "SPY", "consensus": real_consensus(), "message": "m"},
        ])
        rows = {r["ticker"]: r for r in client.post("/api/cron/run-now").json()["results"]}
        assert rows["AAPL"]["consensus_withheld"] is True
        assert rows["SPY"]["consensus_withheld"] is False

    def test_committee_history_keeps_flag(self, client, monkeypatch, fake_data, history_dir):
        import dashboard.routes.committee as committee

        # Real personas run on the hand-built context; only the consensus is faked.
        monkeypatch.setattr(committee, "get_coordinator", lambda: FakeCoordinator(PLAN))
        resp = client.post("/api/committee", json={"ticker": "AAPL", "question": "q"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["verdict"]["withheld"] is True
        rec = history_dir.list_history()[0]
        assert rec["consensus_withheld"] is True

    def _ws_workflow(self, client, monkeypatch, ticker):
        import augur.registry as registry

        monkeypatch.setattr(registry, "DecisionCoordinator", lambda reg: FakeCoordinator(PLAN))
        with client.websocket_connect("/ws/workflow") as ws:
            ws.send_json({"ticker": ticker, "steps": "fetch,analyze,consensus,committee"})
            while True:
                msg = ws.receive_json()
                if msg.get("type") in ("done", "error"):
                    return msg

    def test_ws_workflow_withheld(self, client, monkeypatch, fake_data):
        msg = self._ws_workflow(client, monkeypatch, "AAPL")
        cons, comm = msg["results"]["consensus"], msg["results"]["committee"]
        assert cons["withheld"] is True and cons["kelly_pct"] == 0.0
        assert comm["verdict"] == "withheld" and comm["score"] is None
        assert comm["abstained"] == 2 and sum(comm["vote"].values()) == 1

    def test_ws_workflow_real_fund(self, client, monkeypatch, fake_data):
        msg = self._ws_workflow(client, monkeypatch, "SPY")
        cons, comm = msg["results"]["consensus"], msg["results"]["committee"]
        assert "withheld" not in cons and cons["score"] == 7.4
        assert comm["verdict"] == "bullish" and comm["score"] == 7.4


# ---------------------------------------------------------------------------
# Debate (workflow step and MCP tool)
# ---------------------------------------------------------------------------

class TestDebate:
    @pytest.mark.parametrize("ticker,signal,score", [("AAPL", "withheld", None),
                                                     ("SPY", "bullish", 7.4)])
    def test_workflow_debate_step(self, monkeypatch, fake_data, ticker, signal, score):
        import augur.registry as registry
        from augur.workflow import run_workflow

        monkeypatch.setattr(registry, "DecisionCoordinator", lambda reg: FakeCoordinator(PLAN))
        debate = run_workflow(ticker, steps="fetch,debate")["results"]["debate"]
        assert (debate["signal"], debate["score"]) == (signal, score)

    def test_mcp_debate(self, monkeypatch):
        pytest.importorskip("mcp")
        import augur.registry as registry
        from tests.test_etf_output import _call_tool

        monkeypatch.setattr(registry, "DecisionCoordinator", lambda reg: FakeCoordinator(PLAN))
        text = _call_tool("augur_debate", {"ticker": "AAPL", "price": 210})
        assert "WITHHELD (fund)" in text and "Score: --" in text
        text = _call_tool("augur_debate", {"ticker": "SPY", "price": 600, "asset_type": "etf"})
        assert "Score: 7.4/10" in text


# ---------------------------------------------------------------------------
# Dashboard templates (static checks; the JS has no test runner)
# ---------------------------------------------------------------------------

def _tpl(name):
    return (DASH / "templates" / name).read_text(encoding="utf-8")


class TestTemplates:
    def test_shared_js_helpers_in_base(self):
        base = _tpl("base.html")
        for fn in ("function augurIsWithheld(", "function augurWithheldLabel(",
                   "function augurScoreText("):
            assert fn in base

    @pytest.mark.parametrize("page", ["history.html", "scanner.html", "watchlist.html",
                                      "signals.html", "portfolio.html", "index.html", "stocks.html"])
    def test_pages_use_withheld_helpers(self, page):
        assert "augurIsWithheld(" in _tpl(page) or "consensus_withheld" in _tpl(page)

    def test_history_page_no_raw_score(self):
        html = _tpl("history.html")
        assert "(rec.score || 0).toFixed(1)" not in html
        assert "augurScoreText(rec, rec.score" in html

    def test_signals_average_skips_withheld(self):
        html = _tpl("signals.html")
        assert "if (augurIsWithheld(r)) continue;" in html

    def test_i18n_keys_in_all_languages(self):
        js = (DASH / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
        for key in ("fund-withheld-tip", "committee-all-agents"):
            assert js.count(f'"{key}"') == 4, key

    def test_committee_zero_selection_means_all(self):
        html = _tpl("committee.html")
        assert "function _updateSelectedCount()" in html
        assert "_t('committee-all-agents'" in html
        assert "'0 ' + _t('committee-agents-unit'" not in html


# ---------------------------------------------------------------------------
# CLI table alignment
# ---------------------------------------------------------------------------

class TestTableWidth:
    def test_emoji_and_cjk_columns_line_up(self, monkeypatch):
        from augur.cli_format import display_width, format_table

        monkeypatch.delenv("NO_COLOR", raising=False)
        assert display_width("🟢 bullish") == 10
        assert display_width("巴菲特") == 6
        table = format_table(["Agent", "Signal", "Score"],
                             [["Ray Dalio", "🟡 neutral", "5.0/10"],
                              ["巴菲特", "🟢 bullish", "7.0/10"],
                              ["Graham", "[HOLD] neutral", "5.0/10"]])
        widths = {display_width(line) for line in table.splitlines()}
        assert len(widths) == 1, table
        # The "|" separators sit in the same terminal column on every line.
        cols = set()
        for line in table.splitlines()[2:]:
            first = line.index("|")
            cols.add(display_width(line[:first]))
        assert len(cols) == 1, table

    def test_box_title_border_matches_bottom(self):
        from augur.cli_format import display_width, format_box

        lines = format_box(["Signal:     🟢 BULLISH", "Score: 7"], title="AAPL Consensus").splitlines()
        assert len({display_width(line) for line in lines}) == 1
