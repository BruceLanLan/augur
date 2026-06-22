# -*- coding: utf-8 -*-
"""Tests for v10.15: first-class augur workflow CLI, API, and MCP."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from augur.cli import main
from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.registry import DecisionCoordinator


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def workflow_result():
    return {
        "ticker": "AAPL",
        "steps": ["fetch", "analyze", "consensus", "committee"],
        "results": {
            "fetch": {"price": 190.0, "pe": 28.0, "sector": "Technology", "industry": "Consumer Electronics"},
            "analyze": {
                "buffett": {
                    "agent_name": "Warren Buffett",
                    "signal": "bullish",
                    "score": 7.5,
                    "confidence": 0.8,
                }
            },
            "consensus": {
                "signal": "bullish",
                "score": 7.2,
                "confidence": 0.75,
                "reasoning": "Strong moat",
                "kelly_pct": 12.0,
            },
            "committee": {
                "question": "Should we invest in AAPL?",
                "verdict": "bullish",
                "score": 7.2,
                "vote": {"bullish": 12, "neutral": 4, "bearish": 2},
                "opinions": [],
            },
        },
        "summary": "═══ Augur Workflow: AAPL ═══",
    }


@pytest.fixture
def mock_ctx():
    return MarketContext(ticker="AAPL", pe=28, roe=0.55, gross_margins=0.46, price=190.0)


@pytest.fixture
def mock_response():
    return AgentResponse(
        agent_id="buffett",
        agent_name="Warren Buffett",
        signal=SignalType.BULLISH,
        confidence=0.8,
        score=7.5,
        reasoning="Strong moat",
    )


class TestWorkflowModule:
    def test_parse_steps_defaults(self):
        from augur.workflow import parse_steps, DEFAULT_STEPS

        assert parse_steps("") == DEFAULT_STEPS.split(",")

    def test_parse_steps_invalid(self):
        from augur.workflow import parse_steps

        with pytest.raises(ValueError, match="Unknown step"):
            parse_steps("fetch,not_a_step")


class TestWorkflowCLI:
    def test_workflow_help(self, runner):
        result = runner.invoke(main, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output
        assert "--steps" in result.output
        assert "fetch,analyze,consensus,committee" in result.output

    def test_workflow_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "workflow" in result.output

    def test_workflow_runs_text(self, runner, workflow_result):
        with patch("augur.workflow.run_workflow", return_value=workflow_result):
            result = runner.invoke(main, [
                "workflow", "AAPL",
                "--steps", "fetch,analyze,consensus,committee",
            ])
        assert result.exit_code == 0
        assert "Augur Workflow: AAPL" in result.output
        assert "Running workflow for AAPL" in result.output

    def test_workflow_json_output(self, runner, workflow_result):
        with patch("augur.workflow.run_workflow", return_value=workflow_result):
            result = runner.invoke(main, [
                "workflow", "AAPL",
                "--steps", "fetch,consensus",
                "--json",
            ])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ticker"] == "AAPL"
        assert "consensus" in payload["results"]
        assert "summary" not in payload

    def test_workflow_invalid_step_exits(self, runner):
        result = runner.invoke(main, ["workflow", "AAPL", "--steps", "fetch,bogus"])
        assert result.exit_code == 1
        assert "Unknown step" in result.output
        assert "Valid steps" in result.output


class TestWorkflowAPI:
    def test_workflow_endpoint(self, workflow_result, monkeypatch):
        monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
        from augur.api import app

        client = TestClient(app)
        with patch("augur.workflow.run_workflow", return_value=workflow_result):
            resp = client.post(
                "/api/workflow",
                json={
                    "ticker": "AAPL",
                    "steps": "fetch,analyze,consensus,committee",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["ticker"] == "AAPL"
        assert "committee" in data["results"]
        assert "timestamp" in data

    def test_workflow_invalid_ticker(self, monkeypatch):
        monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
        from augur.api import app

        client = TestClient(app)
        resp = client.post("/api/workflow", json={"ticker": "BAD@TICK"})
        assert resp.status_code == 400

    def test_workflow_invalid_step(self, monkeypatch):
        monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
        from augur.api import app

        client = TestClient(app)
        with patch("augur.workflow.run_workflow", side_effect=ValueError("Unknown step 'nope'")):
            resp = client.post("/api/workflow", json={"ticker": "AAPL", "steps": "nope"})
        assert resp.status_code == 400


class TestWorkflowMCP:
    def test_augur_workflow_tool(self, workflow_result):
        from augur.mcp_server import _run_workflow_tool

        with patch("augur.workflow.run_workflow", return_value=workflow_result):
            text = _run_workflow_tool("AAPL", steps="fetch,analyze,consensus,committee")
        assert "Workflow complete" in text
        assert "Augur Workflow: AAPL" in text

    def test_augur_workflow_invalid_step(self):
        from augur.mcp_server import _run_workflow_tool

        with patch("augur.workflow.run_workflow", side_effect=ValueError("Unknown step 'bad'")):
            text = _run_workflow_tool("AAPL", steps="bad")
        assert "Unknown step" in text
        assert "Valid steps" in text

    def test_augur_workflow_invalid_ticker(self):
        from augur.mcp_server import _run_workflow_tool

        text = _run_workflow_tool("BAD@TICK")
        assert "Invalid ticker" in text
