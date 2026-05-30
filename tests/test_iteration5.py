# -*- coding: utf-8 -*-
"""Tests for iteration 5 security fixes, deep merge, and concurrency protection."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from augur.personas.base import MarketContext


class TestEvalSandbox:
    """Test AST-based safe evaluation replaces vulnerable eval()."""

    def _make_context(self, **kwargs):
        defaults = {"ticker": "TEST", "pe": 30, "roe": 0.55, "gross_margins": 0.46}
        defaults.update(kwargs)
        return MarketContext(**defaults)

    def test_legitimate_simple_comparison(self):
        """Simple comparisons like 'pe > 25' work correctly."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context(pe=30)
        assert _eval_rule_condition("pe > 25", ctx) is True
        assert _eval_rule_condition("pe < 25", ctx) is False

    def test_legitimate_compound_condition(self):
        """Compound conditions like 'roe > 0.15 and gross_margins > 0.4' work."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context(roe=0.55, gross_margins=0.46)
        assert _eval_rule_condition("roe > 0.15 and gross_margins > 0.4", ctx) is True
        assert _eval_rule_condition("roe > 0.15 and gross_margins > 0.5", ctx) is False

    def test_legitimate_arithmetic(self):
        """Arithmetic in conditions works."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context(pe=30)
        assert _eval_rule_condition("pe > 20 + 5", ctx) is True

    def test_class_introspection_blocked(self):
        """Class introspection attack is blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        malicious = "().__class__.__bases__[0].__subclasses__()"
        assert _eval_rule_condition(malicious, ctx) is False

    def test_import_blocked(self):
        """__import__('os') attack is blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("__import__('os')", ctx) is False

    def test_function_calls_blocked(self):
        """Function calls like print('hello') are blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("print('hello')", ctx) is False

    def test_lambda_blocked(self):
        """Lambda expressions are blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("(lambda: 1)()", ctx) is False

    def test_attribute_access_blocked(self):
        """Attribute access like ().__class__ is blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("().__class__", ctx) is False

    def test_list_comprehension_blocked(self):
        """List comprehensions are blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("[x for x in range(10)]", ctx) is False

    def test_subscript_blocked(self):
        """Subscript access is blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("().__class__.__bases__[0]", ctx) is False

    def test_unknown_name_blocked(self):
        """Unknown names not in context are blocked."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("unknown_var > 5", ctx) is False

    def test_invalid_syntax_returns_false(self):
        """Invalid syntax returns False gracefully."""
        from augur.persona_loader import _eval_rule_condition

        ctx = self._make_context()
        assert _eval_rule_condition("pe >>>> 25", ctx) is False


class TestSoulSecurity:
    """Test soul.py directory traversal prevention."""

    def test_path_traversal_blocked(self):
        """inject_soul raises ValueError on path traversal attempt."""
        from augur.soul import inject_soul

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Path traversal detected"):
                inject_soul("../../etc/evil", "buffett", format="hermes", output_dir=tmpdir)

    def test_path_traversal_blocked_raw_format(self):
        """inject_soul also blocks traversal in raw format."""
        from augur.soul import inject_soul

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Path traversal detected"):
                inject_soul("../../etc/evil", "buffett", format="raw", output_dir=tmpdir)

    def test_invalid_format_rejected(self):
        """inject_soul raises ValueError on invalid format."""
        from augur.soul import inject_soul

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Unknown format"):
                inject_soul("test", "buffett", format="invalid", output_dir=tmpdir)

    def test_valid_format_hermes(self):
        """inject_soul works with hermes format."""
        from augur.soul import inject_soul

        with tempfile.TemporaryDirectory() as tmpdir:
            result = inject_soul("test-profile", "buffett", format="hermes", output_dir=tmpdir)
            assert result.exists()
            assert "soul.md" in str(result)
            content = result.read_text()
            assert "Warren Buffett" in content

    def test_valid_format_claude(self):
        """inject_soul works with claude format."""
        from augur.soul import inject_soul

        with tempfile.TemporaryDirectory() as tmpdir:
            result = inject_soul("test-profile", "buffett", format="claude", output_dir=tmpdir)
            assert result.exists()
            assert "claude.json" in str(result)

    def test_valid_format_raw(self):
        """inject_soul works with raw format."""
        from augur.soul import inject_soul

        with tempfile.TemporaryDirectory() as tmpdir:
            result = inject_soul("test-profile", "buffett", format="raw", output_dir=tmpdir)
            assert result.exists()
            content = result.read_text()
            assert "Warren Buffett" in content


class TestCronDeepMerge:
    """Test cron config deep merge preserves nested defaults."""

    def test_partial_schedule_preserves_timezone(self):
        """User provides only cron, timezone default is preserved."""
        from augur.cron import _deep_merge, DEFAULT_CONFIG

        user_config = {"schedule": {"cron": "0 8 * * *"}}
        merged = _deep_merge(DEFAULT_CONFIG, user_config)
        assert merged["schedule"]["cron"] == "0 8 * * *"
        assert merged["schedule"]["timezone"] == "Asia/Shanghai"

    def test_partial_notifications_preserves_defaults(self):
        """User enables telegram but other fields are preserved from defaults."""
        from augur.cron import _deep_merge, DEFAULT_CONFIG

        user_config = {"notifications": {"telegram": {"enabled": True}}}
        merged = _deep_merge(DEFAULT_CONFIG, user_config)
        assert merged["notifications"]["telegram"]["enabled"] is True
        assert merged["notifications"]["telegram"]["chat_id"] == ""
        assert merged["notifications"]["slack"]["enabled"] is False

    def test_full_override_works(self):
        """User can fully override nested values."""
        from augur.cron import _deep_merge, DEFAULT_CONFIG

        user_config = {
            "schedule": {"cron": "30 10 * * 1-5", "timezone": "US/Eastern"},
            "notifications": {
                "telegram": {"enabled": True, "chat_id": "123", "token": "abc"},
            },
        }
        merged = _deep_merge(DEFAULT_CONFIG, user_config)
        assert merged["schedule"]["cron"] == "30 10 * * 1-5"
        assert merged["schedule"]["timezone"] == "US/Eastern"
        assert merged["notifications"]["telegram"]["enabled"] is True
        assert merged["notifications"]["telegram"]["chat_id"] == "123"
        assert merged["notifications"]["telegram"]["token"] == "abc"

    def test_non_dict_override_replaces_fully(self):
        """Non-dict values in override fully replace base values."""
        from augur.cron import _deep_merge

        base = {"a": {"x": 1, "y": 2}, "b": [1, 2, 3]}
        override = {"b": [4, 5]}
        merged = _deep_merge(base, override)
        assert merged["b"] == [4, 5]
        assert merged["a"] == {"x": 1, "y": 2}

    def test_load_watchlist_deep_merge_with_file(self):
        """load_watchlist does deep merge when reading from file."""
        import yaml
        from augur.cron import load_watchlist

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "watchlist.yaml"
            # Write partial config (schedule.cron but no timezone)
            partial_config = {"schedule": {"cron": "0 8 * * *"}}
            tmp_path.write_text(yaml.dump(partial_config))
            with patch("augur.cron.WATCHLIST_PATH", tmp_path):
                config = load_watchlist()
                assert config["schedule"]["cron"] == "0 8 * * *"
                assert config["schedule"]["timezone"] == "Asia/Shanghai"


class TestCronConcurrency:
    """Test start_scheduler concurrency protection."""

    def test_add_job_has_max_instances(self):
        """start_scheduler uses max_instances=1 in add_job call."""
        import inspect
        from augur.cron import start_scheduler

        source = inspect.getsource(start_scheduler)
        assert "max_instances=1" in source

    def test_pidfile_logic_exists(self):
        """start_scheduler has pidfile-based concurrency protection."""
        import inspect
        from augur.cron import start_scheduler

        source = inspect.getsource(start_scheduler)
        assert "scheduler.pid" in source
        assert "os.kill" in source
        assert "os.getpid()" in source
