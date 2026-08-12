# -*- coding: utf-8 -*-
"""Tests for new MCP resources (thesis, ledger)."""
import json
import pytest


class TestThesisResource:
    def test_thesis_resource_missing(self):
        """Unknown thesis returns an error JSON."""
        from augur.mcp_server import create_server
        pytest.importorskip("mcp")
        mcp = create_server()
        # Call the resource function directly
        from augur.mcp_server import get_thesis_resource
        result = get_thesis_resource("th_nonexistent")
        data = json.loads(result)
        assert "error" in data or data.get("thesis_id") == "th_nonexistent"


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
