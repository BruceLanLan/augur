# -*- coding: utf-8 -*-
"""Tests for augur.rules - Notification Rules Engine"""

import os
import tempfile
import pytest
from augur.rules import RulesEngine, Rule, NotificationDispatcher, OPERATORS


class TestRule:
    def test_rule_creation(self):
        """Rule can be created with all fields."""
        rule = Rule(
            id="test-1",
            name="High Score Alert",
            conditions=[{"field": "consensus_score", "op": ">", "value": 8}],
            actions=[{"channel": "telegram", "message": "Score high!"}],
            enabled=True,
        )
        assert rule.id == "test-1"
        assert rule.name == "High Score Alert"
        assert len(rule.conditions) == 1
        assert len(rule.actions) == 1

    def test_rule_to_dict(self):
        """Rule serializes to dict."""
        rule = Rule(id="r1", name="Test", conditions=[], actions=[])
        d = rule.to_dict()
        assert d["id"] == "r1"
        assert d["name"] == "Test"
        assert d["enabled"] is True

    def test_rule_from_dict(self):
        """Rule deserializes from dict."""
        data = {
            "id": "r2",
            "name": "From Dict",
            "conditions": [{"field": "score", "op": ">=", "value": 7}],
            "actions": [{"channel": "slack", "message": "hi"}],
            "enabled": False,
        }
        rule = Rule.from_dict(data)
        assert rule.id == "r2"
        assert rule.enabled is False


class TestNotificationDispatcher:
    def test_dispatch_telegram(self):
        """Dispatch to telegram channel records message."""
        d = NotificationDispatcher()
        result = d.dispatch("telegram", "Alert!")
        assert result is True
        assert len(d.get_sent()) == 1
        assert d.get_sent()[0]["channel"] == "telegram"

    def test_dispatch_all_channels(self):
        """All supported channels work."""
        d = NotificationDispatcher()
        for ch in ["telegram", "slack", "wechat", "lark"]:
            assert d.dispatch(ch, f"msg to {ch}") is True
        assert len(d.get_sent()) == 4

    def test_dispatch_unsupported_channel(self):
        """Unsupported channel returns False."""
        d = NotificationDispatcher()
        assert d.dispatch("email", "test") is False
        assert len(d.get_sent()) == 0

    def test_clear(self):
        """Clear removes all sent records."""
        d = NotificationDispatcher()
        d.dispatch("slack", "hi")
        d.clear()
        assert len(d.get_sent()) == 0


class TestRulesEngine:
    def _make_engine(self, tmp_path=None):
        """Create a RulesEngine with a temporary rules file."""
        if tmp_path is None:
            tmp_path = tempfile.mkdtemp()
        path = os.path.join(tmp_path, "rules.yaml")
        return RulesEngine(rules_path=path)

    def test_add_and_list_rules(self, tmp_path):
        """Adding rules persists and lists them."""
        engine = self._make_engine(str(tmp_path))
        rule = Rule(id="", name="Test Rule", conditions=[], actions=[])
        created = engine.add_rule(rule)
        assert created.id != ""
        assert len(engine.get_rules()) == 1

    def test_remove_rule(self, tmp_path):
        """Removing a rule works."""
        engine = self._make_engine(str(tmp_path))
        rule = Rule(id="del-me", name="Delete", conditions=[], actions=[])
        engine.add_rule(rule)
        assert engine.remove_rule("del-me") is True
        assert len(engine.get_rules()) == 0

    def test_remove_nonexistent(self, tmp_path):
        """Removing nonexistent rule returns False."""
        engine = self._make_engine(str(tmp_path))
        assert engine.remove_rule("nope") is False

    def test_evaluate_condition_gt(self, tmp_path):
        """Evaluate > operator."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "score", "op": ">", "value": 7}
        assert engine.evaluate_condition(cond, {"score": 8}) is True
        assert engine.evaluate_condition(cond, {"score": 5}) is False

    def test_evaluate_condition_lt(self, tmp_path):
        """Evaluate < operator."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "price", "op": "<", "value": 100}
        assert engine.evaluate_condition(cond, {"price": 50}) is True
        assert engine.evaluate_condition(cond, {"price": 200}) is False

    def test_evaluate_condition_eq(self, tmp_path):
        """Evaluate == operator."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "signal", "op": "==", "value": "bullish"}
        assert engine.evaluate_condition(cond, {"signal": "bullish"}) is True
        assert engine.evaluate_condition(cond, {"signal": "bearish"}) is False

    def test_evaluate_condition_contains(self, tmp_path):
        """Evaluate contains operator."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "reasoning", "op": "contains", "value": "strong"}
        assert engine.evaluate_condition(cond, {"reasoning": "Very strong buy"}) is True
        assert engine.evaluate_condition(cond, {"reasoning": "Weak sell"}) is False

    def test_evaluate_condition_gte_lte_neq(self, tmp_path):
        """Evaluate >=, <=, != operators."""
        engine = self._make_engine(str(tmp_path))
        assert engine.evaluate_condition({"field": "x", "op": ">=", "value": 5}, {"x": 5}) is True
        assert engine.evaluate_condition({"field": "x", "op": "<=", "value": 5}, {"x": 5}) is True
        assert engine.evaluate_condition({"field": "x", "op": "!=", "value": 5}, {"x": 3}) is True
        assert engine.evaluate_condition({"field": "x", "op": "!=", "value": 5}, {"x": 5}) is False

    def test_evaluate_triggers_actions(self, tmp_path):
        """evaluate() dispatches actions when conditions match."""
        engine = self._make_engine(str(tmp_path))
        rule = Rule(
            id="r1",
            name="High Score",
            conditions=[{"field": "consensus_score", "op": ">", "value": 8}],
            actions=[{"channel": "telegram", "message": "Score is {consensus_score}!"}],
            enabled=True,
        )
        engine.add_rule(rule)

        triggered = engine.evaluate({"consensus_score": 9.5})
        assert len(triggered) == 1
        assert triggered[0]["rule_name"] == "High Score"
        assert "9.5" in triggered[0]["message"]
        assert len(engine.dispatcher.get_sent()) == 1

    def test_evaluate_disabled_rule_skipped(self, tmp_path):
        """Disabled rules are not evaluated."""
        engine = self._make_engine(str(tmp_path))
        rule = Rule(
            id="r2",
            name="Disabled",
            conditions=[{"field": "score", "op": ">", "value": 0}],
            actions=[{"channel": "slack", "message": "hi"}],
            enabled=False,
        )
        engine.add_rule(rule)
        triggered = engine.evaluate({"score": 10})
        assert len(triggered) == 0

    def test_yaml_persistence(self, tmp_path):
        """Rules persist to and load from YAML."""
        path = str(tmp_path / "rules.yaml")
        engine1 = RulesEngine(rules_path=path)
        engine1.add_rule(Rule(id="persist", name="Persisted", conditions=[{"field": "x", "op": ">", "value": 1}], actions=[]))

        # Create new engine pointing to same file
        engine2 = RulesEngine(rules_path=path)
        rules = engine2.get_rules()
        assert len(rules) == 1
        assert rules[0].name == "Persisted"

    def test_nested_field_access(self, tmp_path):
        """Conditions can reference nested fields with dot notation."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "consensus.score", "op": ">", "value": 7}
        data = {"consensus": {"score": 8.5}}
        assert engine.evaluate_condition(cond, data) is True

    def test_multi_condition_and_requires_all(self, tmp_path):
        """All conditions must match (AND); one failure blocks the rule."""
        engine = self._make_engine(str(tmp_path))
        rule = Rule(
            id="and-1",
            name="Score and Signal",
            conditions=[
                {"field": "consensus_score", "op": ">", "value": 7},
                {"field": "signal", "op": "==", "value": "bullish"},
            ],
            actions=[{"channel": "slack", "message": "Both matched"}],
        )
        engine.add_rule(rule)

        partial = engine.evaluate({"consensus_score": 8.5, "signal": "bearish"})
        assert len(partial) == 0

        full = engine.evaluate({"consensus_score": 8.5, "signal": "bullish"})
        assert len(full) == 1
        assert full[0]["rule_name"] == "Score and Signal"

    def test_malformed_yaml_starts_empty(self, tmp_path):
        """Corrupt rules YAML must not crash; engine loads zero rules."""
        path = tmp_path / "rules.yaml"
        path.write_text("rules:\n  - id: [broken\n    name: oops", encoding="utf-8")
        engine = RulesEngine(rules_path=str(path))
        assert engine.get_rules() == []

    def test_invalid_operator_returns_false(self, tmp_path):
        """Unknown operator evaluates to False (does not raise)."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "score", "op": "~~invalid~~", "value": 1}
        assert engine.evaluate_condition(cond, {"score": 5}) is False

    def test_missing_field_returns_false(self, tmp_path):
        """Condition referencing absent field evaluates to False."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "nonexistent", "op": ">", "value": 0}
        assert engine.evaluate_condition(cond, {"other": 1}) is False

    def test_nested_field_through_non_dict(self, tmp_path):
        """Dot-notation into a non-dict segment returns None -> False."""
        engine = self._make_engine(str(tmp_path))
        cond = {"field": "a.b.c", "op": ">", "value": 0}
        # 'a' is a string, so further traversal must not crash
        assert engine.evaluate_condition(cond, {"a": "string"}) is False

    def test_get_rule_by_id(self, tmp_path):
        """get_rule returns the matching rule or None."""
        engine = self._make_engine(str(tmp_path))
        engine.add_rule(Rule(id="find-me", name="Find", conditions=[], actions=[]))
        engine.add_rule(Rule(id="other", name="Other", conditions=[], actions=[]))
        found = engine.get_rule("find-me")
        assert found is not None and found.name == "Find"
        assert engine.get_rule("does-not-exist") is None

    def test_message_template_substitution_nested(self, tmp_path):
        """Template variables substitute nested fields via dot notation."""
        engine = self._make_engine(str(tmp_path))
        rule = Rule(
            id="tpl-1",
            name="Tpl",
            conditions=[{"field": "consensus.score", "op": ">", "value": 0}],
            actions=[{"channel": "lark", "message": "{ticker} scored {consensus.score}"}],
        )
        engine.add_rule(rule)
        triggered = engine.evaluate({"ticker": "AAPL", "consensus": {"score": 9.0}})
        assert len(triggered) == 1
        msg = triggered[0]["message"]
        assert "AAPL" in msg and "9.0" in msg

    def test_rule_with_multiple_actions_dispatches_each(self, tmp_path):
        """A triggered rule with N actions dispatches N notifications."""
        engine = self._make_engine(str(tmp_path))
        rule = Rule(
            id="multi-act",
            name="Multi",
            conditions=[{"field": "x", "op": "==", "value": 1}],
            actions=[
                {"channel": "telegram", "message": "a"},
                {"channel": "slack", "message": "b"},
                {"channel": "lark", "message": "c"},
            ],
        )
        engine.add_rule(rule)
        triggered = engine.evaluate({"x": 1})
        assert len(triggered) == 3
        channels = {t["action"]["channel"] for t in triggered}
        assert channels == {"telegram", "slack", "lark"}
        assert len(engine.dispatcher.get_sent()) == 3

    def test_malformed_rule_entries_skipped(self, tmp_path):
        """Bad individual rule entries are skipped; valid ones still load."""
        import yaml as _yaml
        path = tmp_path / "rules.yaml"
        data = {
            "rules": [
                {"id": "good", "name": "Good", "conditions": [], "actions": []},
                "not-a-dict",
                {"id": "good2", "name": "Good2", "conditions": [], "actions": []},
            ]
        }
        path.write_text(_yaml.dump(data), encoding="utf-8")
        engine = RulesEngine(rules_path=str(path))
        names = [r.name for r in engine.get_rules()]
        assert "Good" in names and "Good2" in names
        assert len(engine.get_rules()) == 2

    def test_yaml_errors_handled_cleanly(self, tmp_path):
        """Both bad YAML and malformed persona-shaped YAML raise no exception;
        engine starts with an empty rule set in both cases.
        Regression test for yaml.scanner.ScannerError AttributeError on
        minimal PyYAML builds: catching yaml.YAMLError (the base class)
        must suffice.
        """
        # Case 1: structurally broken YAML (truncated flow sequence)
        bad_path = tmp_path / "bad.yaml"
        bad_path.write_text("rules:\n  - id: [unterminated\n", encoding="utf-8")
        bad_engine = RulesEngine(rules_path=str(bad_path))
        assert bad_engine.get_rules() == []

        # Case 2: malformed persona-shaped YAML (looks like a persona config
        # with an unclosed mapping under a non-'rules' root key)
        persona_path = tmp_path / "persona.yaml"
        persona_path.write_text(
            "persona:\n  name: lynch\n  style: { value: aggressive\n",
            encoding="utf-8",
        )
        persona_engine = RulesEngine(rules_path=str(persona_path))
        assert persona_engine.get_rules() == []
