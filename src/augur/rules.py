# -*- coding: utf-8 -*-
"""
augur.rules - Notification Rules Engine

Provides a rules engine that evaluates analysis results against
user-defined conditions and dispatches notifications to multiple channels.
Rules are stored in ~/.augur/rules.yaml.

Architecture:
    - Rule: Dataclass representing a condition-action pair
    - RulesEngine: Loads rules from YAML, evaluates them against data dicts
    - NotificationDispatcher: Routes messages to telegram, slack, wechat, lark

Condition Evaluation:
    - Supports operators: >, <, >=, <=, ==, !=, contains
    - Nested field access via dot notation (e.g., "consensus.score")
    - All conditions in a rule must match (AND logic)

Notification Channels:
    - telegram: via augur.bots.telegram_bot
    - slack: via augur.bots.slack_bot
    - wechat: via augur.bots.wechat_bot
    - lark: via augur.bots.lark_bot
    - Falls back to in-memory logging if bot modules are unavailable

Error Handling:
    - Malformed YAML: silently starts with empty rules
    - Missing/corrupt rules file: returns empty rule set
    - Invalid rule entries: skipped individually (other rules still load)
    - Bot dispatch failures: logged but do not raise

Usage:
    engine = RulesEngine()
    engine.add_rule(Rule(id="1", name="Alert", conditions=[...], actions=[...]))
    triggered = engine.evaluate({"consensus_score": 8.5, "ticker": "AAPL"})
"""

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class Rule:
    """A notification rule definition."""
    id: str
    name: str
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "conditions": self.conditions,
            "actions": self.actions,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Unnamed Rule"),
            conditions=data.get("conditions", []),
            actions=data.get("actions", []),
            enabled=data.get("enabled", True),
        )


# Supported comparison operators
OPERATORS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "contains": lambda a, b: str(b) in str(a),
}


class NotificationDispatcher:
    """Dispatches notifications to various channels.

    Supported channels: telegram, slack, wechat, lark.
    Attempts to use real bot infrastructure from augur.bots when available,
    falls back to in-memory logging for testing.
    """

    def __init__(self):
        self._sent: List[Dict[str, Any]] = []

    def dispatch(self, channel: str, message: str, **kwargs) -> bool:
        """Send notification to the specified channel.

        Args:
            channel: One of 'telegram', 'slack', 'wechat', 'lark'
            message: Notification message text
            **kwargs: Additional channel-specific parameters

        Returns:
            True if dispatched successfully (always True in mock mode)
        """
        supported = {"telegram", "slack", "wechat", "lark"}
        if channel not in supported:
            return False

        # Attempt to dispatch via real bot infrastructure
        sent_via_bot = self._dispatch_via_bot(channel, message, **kwargs)

        record = {
            "channel": channel,
            "message": message,
            "kwargs": kwargs,
            "sent_via_bot": sent_via_bot,
        }
        self._sent.append(record)
        return True

    def _dispatch_via_bot(self, channel: str, message: str, **kwargs) -> bool:
        """Try to dispatch via the actual bot infrastructure in augur.bots.

        Returns True if dispatched via real bot, False if falling back to mock.
        """
        try:
            if channel == "telegram":
                from augur.bots.telegram_bot import send_notification
                send_notification(message, **kwargs)
                return True
            elif channel == "slack":
                from augur.bots.slack_bot import send_notification
                send_notification(message, **kwargs)
                return True
            elif channel == "wechat":
                from augur.bots.wechat_bot import send_notification
                send_notification(message, **kwargs)
                return True
            elif channel == "lark":
                from augur.bots.lark_bot import send_notification
                send_notification(message, **kwargs)
                return True
        except (ImportError, AttributeError, Exception):
            # Bot module not configured or send_notification not available
            pass
        return False

    def get_sent(self) -> List[Dict[str, Any]]:
        """Get all dispatched notifications (for testing)."""
        return list(self._sent)

    def clear(self) -> None:
        """Clear sent notifications log."""
        self._sent.clear()


class RulesEngine:
    """Evaluates rules against analysis results and dispatches notifications.

    Rules are stored in ~/.augur/rules.yaml.
    """

    def __init__(self, rules_path: Optional[str] = None):
        if rules_path:
            self._rules_path = Path(rules_path)
        else:
            self._rules_path = Path.home() / ".augur" / "rules.yaml"
        self._rules: List[Rule] = []
        self._dispatcher = NotificationDispatcher()
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from YAML file. Handles malformed YAML gracefully."""
        if not self._rules_path.exists():
            self._rules = []
            return

        if yaml is None:
            self._rules = []
            return

        try:
            content = self._rules_path.read_text(encoding="utf-8")
            if not content or not content.strip():
                self._rules = []
                return
            data = yaml.safe_load(content)
            if data and isinstance(data, dict) and "rules" in data:
                rules_list = data["rules"]
                if not isinstance(rules_list, list):
                    self._rules = []
                    return
                self._rules = []
                for r in rules_list:
                    if isinstance(r, dict):
                        try:
                            self._rules.append(Rule.from_dict(r))
                        except (KeyError, TypeError, ValueError):
                            # Skip malformed rule entries
                            continue
            else:
                self._rules = []
        except yaml.YAMLError:
            # Malformed YAML - start with empty rules
            # yaml.YAMLError is the base class for all PyYAML parsing/scanner/parser errors.
            self._rules = []
        except (OSError, IOError):
            # File read error
            self._rules = []
        except Exception:
            # Catch-all for unexpected errors
            self._rules = []

    def _save_rules(self) -> None:
        """Save rules to YAML file."""
        if yaml is None:
            return

        self._rules_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"rules": [r.to_dict() for r in self._rules]}
        self._rules_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    def add_rule(self, rule: Rule) -> Rule:
        """Add a new rule and persist to disk."""
        if not rule.id:
            rule.id = str(uuid.uuid4())
        self._rules.append(rule)
        self._save_rules()
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]
        if len(self._rules) < before:
            self._save_rules()
            return True
        return False

    def get_rules(self) -> List[Rule]:
        """Get all rules."""
        return list(self._rules)

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a specific rule by ID."""
        for r in self._rules:
            if r.id == rule_id:
                return r
        return None

    def evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate a single condition against data.

        Condition format: {"field": "consensus_score", "op": ">", "value": 8}
        """
        field_name = condition.get("field", "")
        op = condition.get("op", "==")
        expected = condition.get("value")

        if op not in OPERATORS:
            return False

        # Get the actual value from data using dot notation
        actual = self._get_nested(data, field_name)
        if actual is None:
            return False

        try:
            # Try numeric comparison first
            if op != "contains":
                actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
                expected_num = float(expected) if not isinstance(expected, (int, float)) else expected
                return OPERATORS[op](actual_num, expected_num)
            else:
                return OPERATORS[op](actual, expected)
        except (ValueError, TypeError):
            # Fall back to string comparison
            return OPERATORS[op](str(actual), str(expected))

    def _get_nested(self, data: Dict[str, Any], key: str) -> Any:
        """Get a potentially nested value from data using dot notation."""
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    def evaluate(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all enabled rules against an analysis result.

        Returns list of triggered actions with their rule info.
        """
        triggered = []

        for rule in self._rules:
            if not rule.enabled:
                continue

            # All conditions must be satisfied (AND logic)
            all_match = True
            for condition in rule.conditions:
                if not self.evaluate_condition(condition, analysis_result):
                    all_match = False
                    break

            if all_match and rule.conditions:
                # Dispatch all actions
                for action in rule.actions:
                    channel = action.get("channel", "")
                    message = action.get("message", f"Rule '{rule.name}' triggered")
                    # Substitute template variables in message
                    message = self._format_message(message, analysis_result)
                    self._dispatcher.dispatch(channel, message)
                    triggered.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "action": action,
                        "message": message,
                    })

        return triggered

    def _format_message(self, template: str, data: Dict[str, Any]) -> str:
        """Format a message template with data values."""
        try:
            # Simple {field} substitution
            import re
            def replacer(m):
                key = m.group(1)
                val = self._get_nested(data, key)
                return str(val) if val is not None else m.group(0)
            return re.sub(r'\{(\w+(?:\.\w+)*)\}', replacer, template)
        except Exception:
            return template

    @property
    def dispatcher(self) -> NotificationDispatcher:
        """Access the notification dispatcher."""
        return self._dispatcher
