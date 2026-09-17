# -*- coding: utf-8 -*-
"""Tests for thesis/questions/decisions REST API."""
import json
import pytest

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    try:
        from dashboard.app import app
        return TestClient(app)
    except Exception:
        pytest.skip("dashboard app not importable")


class TestThesisAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/thesis/list")
        assert resp.status_code == 200
        data = resp.json()
        assert "theses" in data

    def test_create_and_list(self, client):
        resp = client.post("/api/thesis/create", json={
            "ticker": "TEST", "statement": "Test thesis",
            "catalysts": ["c1"], "risks": ["r1"],
            "falsification_conditions": ["condition 1"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        # List filtered by ticker
        resp2 = client.get("/api/thesis/list?ticker=TEST")
        assert resp2.status_code == 200
        items = resp2.json()["theses"]
        assert any(t["statement"] == "Test thesis" for t in items)


class TestQuestionsAPI:
    def test_add_and_list(self, client):
        resp = client.post("/api/questions/add", json={
            "ticker": "QTEST", "question": "Is growth sustainable?",
            "context": "Testing",
        })
        assert resp.status_code == 200
        resp2 = client.get("/api/questions/list?ticker=QTEST")
        assert resp2.status_code == 200
        questions = resp2.json()["questions"]
        assert any(q["question"] == "Is growth sustainable?" for q in questions)


class TestDecisionsAPI:
    def test_record_and_list(self, client):
        resp = client.post("/api/decisions/record", json={
            "ticker": "DTEST", "action": "buy", "reasoning": "test decision",
        })
        assert resp.status_code == 200
        resp2 = client.get("/api/decisions/list?ticker=DTEST")
        assert resp2.status_code == 200
        decisions = resp2.json()["decisions"]
        assert any(d["action"] == "buy" for d in decisions)


def test_thesis_page_renders_all_panels_and_valid_script():
    """The Thesis Journal page never worked: a quoting error broke its script,
    the script looked up a class that does not exist (.tj-journal), and the
    questions / decisions panels sat after {% endblock %} so Jinja dropped them."""
    from fastapi.testclient import TestClient

    from dashboard.app import app

    html = TestClient(app).get("/thesis").text
    assert 'class="thesis-journal"' in html
    assert "querySelector('.tj-journal')" not in html
    assert "openEvidence('' + r + '')" not in html
    for panel in ("tj-active-list", "tj-history-list", "tj-questions-list", "tj-decisions-list"):
        assert f'id="{panel}"' in html, panel


def test_decisions_list_without_ticker_returns_all():
    from fastapi.testclient import TestClient

    from dashboard.app import app

    client = TestClient(app)
    did = client.post("/api/decisions/record", json={"ticker": "LSTALL", "action": "buy", "reasoning": "r"}).json()["decision_id"]
    assert did in {d["decision_id"] for d in client.get("/api/decisions/list").json()["decisions"]}


def test_questions_list_without_ticker_returns_all():
    from fastapi.testclient import TestClient

    from dashboard.app import app

    client = TestClient(app)
    qid = client.post("/api/questions/add", json={"ticker": "QALL", "question": "Is growth durable?"}).json()["question_id"]
    assert qid in {q["question_id"] for q in client.get("/api/questions/list").json()["questions"]}
