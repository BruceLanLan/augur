"""v12: earnings dossier / scorecard endpoints must not return fabricated content.

Evidence-first rule: missing data is reported explicitly as
``{"status": "unavailable", "reason": ...}``; real data comes from the same
builder the CLI uses (``run_earnings_dossier``).
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app

_PLACEHOLDERS = (
    "Supply chain concentration",
    "Pending",
    "Macro headwinds",
    "Regulatory uncertainty",
    "cathie_wood",
    "Will management raise or lower guidance?",
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "data"))
    # The route caches an event service; make sure it is not reused across tests.
    import dashboard.routes.earnings as earnings_routes

    monkeypatch.setattr(earnings_routes, "_EVENT_SERVICE", None)
    return TestClient(app)


def _assert_no_placeholders(payload) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    for marker in _PLACEHOLDERS:
        assert marker not in text, f"placeholder {marker!r} leaked: {text[:300]}"


def test_dossier_unavailable_with_empty_data_dir(client):
    r = client.get("/api/earnings/dossier/ZZZT")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unavailable"
    assert body["reason"]
    assert "dossier" not in body
    _assert_no_placeholders(body)


def test_dossier_uses_cli_builder_with_real_data(client):
    from augur.questions import QuestionQueue, ResearchQuestion

    QuestionQueue.persistent().add(
        ResearchQuestion(question_id="", ticker="ZZZT",
                         question="Does the backlog cover next-year revenue?",
                         context="test", created_at="2026-10-01T00:00:00Z")
    )
    r = client.get("/api/earnings/dossier/zzzt")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    d = body["dossier"]
    assert d["ticker"] == "ZZZT"
    assert d["source"].endswith("run_earnings_dossier")

    from augur.cli_commands.dossier_cmd import run_earnings_dossier

    assert d["text"] == run_earnings_dossier("ZZZT")
    titles = [s["title"] for s in d["sections"]]
    assert "Open Questions" in titles
    assert any("backlog" in line for s in d["sections"] for line in s["lines"])
    _assert_no_placeholders(body)


def test_dossier_rejects_bad_ticker(client):
    assert client.get("/api/earnings/dossier/bad$ticker").status_code == 400


def test_earnings_scorecard_is_explicitly_unavailable(client):
    r = client.get("/api/earnings/scorecard/ZZZT")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unavailable"
    assert body["reason"]
    assert "scorecard" not in body  # no zero-filled stub summary
    _assert_no_placeholders(body)


def test_scorecard_page_api_exists_and_is_unavailable(client):
    r = client.get("/api/scorecard", params={"ticker": "zzzt"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unavailable"
    assert body["ticker"] == "ZZZT"
    assert body["reason"]
    assert body["items"] == []


def test_scorecard_page_api_validates_ticker(client):
    assert client.get("/api/scorecard").status_code == 422
    assert client.get("/api/scorecard", params={"ticker": "bad$t"}).status_code == 400


def test_templates_handle_unavailable_shape():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "templates"
    sc = (root / "scorecard.html").read_text(encoding="utf-8")
    assert "data.status !== 'ok'" in sc and "data.reason" in sc
    eq = (root / "earnings_queue.html").read_text(encoding="utf-8")
    assert "data.reason" in eq
    assert "Array.isArray(d.sections)" in eq


def test_dashboard_shows_the_installed_version():
    """The home page and sidebar used to say 'v8.1.0' whatever was installed."""
    import augur
    from fastapi.testclient import TestClient

    from dashboard.app import app

    html = TestClient(app).get("/").text
    assert f"v{augur.__version__}" in html
    assert "v8.1.0" not in html
