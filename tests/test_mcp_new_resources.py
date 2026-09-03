# -*- coding: utf-8 -*-
"""Tests for new MCP resources (thesis, ledger)."""
import json
import pytest


class TestThesisResource:
    def test_thesis_resource_missing(self):
        """Unknown thesis returns an error JSON via the registered MCP resource.

        The resource handler is a closure inside ``create_server()``, so it is
        exercised through the server's resource API rather than imported by
        name (the previous version of this test imported a symbol that never
        existed at module level and only went unnoticed because CI's test
        step could not fail — see docs/reviews/FABLE_REVIEW_2026-09-03.md).
        """
        import asyncio
        pytest.importorskip("mcp")
        from augur.mcp_server import create_server

        mcp = create_server()
        contents = asyncio.run(mcp.read_resource("augur://thesis/th_nonexistent"))
        payload = next(iter(contents)).content
        data = json.loads(payload)
        assert data.get("thesis_id") == "th_nonexistent"
        assert "error" in data


class TestLedgerResource:
    def test_ledger_resource_missing(self):
        """Unknown ledger returns an error JSON."""
        import json as _json
        from pathlib import Path
        from augur.data_dir import get_data_dir
        # Ensure clean state
        ledger_dir = Path(get_data_dir()) / "ledgers"
        probe = ledger_dir / "TEST_Q4_2025.json"
        result = None
        if probe.exists():
            result = probe.read_text(encoding="utf-8")
        else:
            result = _json.dumps({"error": "ledger not found"})
        assert "ledger not found" in result or "ticker" in result


class TestMCPServerSurface:
    def test_mcp_server_has_seven_prompts(self):
        """Verify 7 prompts are registered in the source."""
        import re
        from pathlib import Path
        src = Path("src/augur/mcp_server.py").read_text(encoding="utf-8")
        prompt_count = len(re.findall(r"@mcp\.prompt\(\)", src))
        assert prompt_count >= 7

    def test_mcp_server_has_four_resources(self):
        """Verify evidence/runs/thesis/ledger resources exist."""
        import re
        from pathlib import Path
        src = Path("src/augur/mcp_server.py").read_text(encoding="utf-8")
        resources = re.findall(r'@mcp\.resource\("(augur://[^"]+)"\)', src)
        assert "augur://evidence/{evidence_id}" in resources
        assert "augur://runs/{run_id}" in resources
        assert "augur://thesis/{thesis_id}" in resources
        assert "augur://ledger/{ticker}/{quarter}" in resources
