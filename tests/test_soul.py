# -*- coding: utf-8 -*-
"""Tests for augur.soul module."""

import tempfile
from pathlib import Path

import pytest


class TestSoul:
    def test_generate_soul_valid_persona(self):
        """generate_soul returns content for a valid persona."""
        from augur.soul import generate_soul

        soul = generate_soul("buffett")
        assert "Warren Buffett" in soul
        assert "Soul Definition" in soul
        assert "Scoring Rules" in soul

    def test_generate_soul_invalid_persona(self):
        """generate_soul raises ValueError for unknown persona."""
        from augur.soul import generate_soul

        with pytest.raises(ValueError):
            generate_soul("nonexistent_persona_xyz")

    def test_soul_injector_class(self):
        """SoulInjector initializes and can generate soul content."""
        from augur.soul import SoulInjector

        injector = SoulInjector()
        assert injector._initialized is True
        soul_text = injector.generate("buffett")
        assert "Warren Buffett" in soul_text

    def test_inject_soul_raw_format(self):
        """inject_soul with raw format creates a file with soul content."""
        from augur.soul import inject_soul

        with tempfile.TemporaryDirectory() as tmpdir:
            path = inject_soul("test-profile", "buffett", format="raw", output_dir=tmpdir)
            assert path.exists()
            content = path.read_text()
            assert "Warren Buffett" in content
