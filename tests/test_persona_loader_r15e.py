# -*- coding: utf-8 -*-
"""Tests for augur.persona_loader (Round 15 Agent E).

Covers:
  - file not found
  - malformed yaml
  - missing required keys
  - valid yaml (basic round-trip)
  - directory bulk-load
"""

import textwrap

import pytest

from augur import persona_loader
from augur.persona_loader import (
    YamlAgent,
    load_persona_yaml,
    load_personas_from_dir,
)


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------

def test_load_persona_yaml_file_not_found(tmp_path):
    """A non-existent path must raise FileNotFoundError."""
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(FileNotFoundError):
        load_persona_yaml(missing)


def test_load_persona_yaml_malformed_yaml(tmp_path):
    """A syntactically broken YAML file must raise (yaml.YAMLError)."""
    import yaml as _yaml

    bad = tmp_path / "bad.yaml"
    bad.write_text("agent_id: [unclosed\nname: : :", encoding="utf-8")
    with pytest.raises(_yaml.YAMLError):
        load_persona_yaml(bad)


def test_load_persona_yaml_missing_required_keys(tmp_path):
    """A YAML missing required keys (agent_id, name, scoring_weights) raises ValueError."""
    spec = tmp_path / "incomplete.yaml"
    # agent_id present, but name and scoring_weights missing
    spec.write_text("identity: just an id-less stub\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required keys"):
        load_persona_yaml(spec)


def test_load_persona_yaml_invalid_agent_id_format(tmp_path):
    """agent_id with uppercase / illegal characters is rejected."""
    spec = tmp_path / "bad_id.yaml"
    spec.write_text(
        textwrap.dedent(
            """\
            agent_id: "Bad-ID!"
            name: Bad
            scoring_weights: {a: 1.0}
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="agent_id"):
        load_persona_yaml(spec)


# ---------------------------------------------------------------------------
# Positive case
# ---------------------------------------------------------------------------

def test_load_persona_yaml_valid_minimal(tmp_path):
    """A minimal valid persona file produces a usable YamlAgent."""
    spec = tmp_path / "ok.yaml"
    spec.write_text(
        textwrap.dedent(
            """\
            agent_id: yaml_minimal
            name: YAML Minimal
            identity: A test persona
            philosophy:
              - buy low
              - sell high
            scoring_weights:
              momentum: 1.0
            factors:
              momentum:
                base: 5
                rules:
                  - if: "price > 0"
                    add: 2
            """
        ),
        encoding="utf-8",
    )
    agent = load_persona_yaml(spec)
    assert isinstance(agent, YamlAgent)
    assert agent.agent_id == "yaml_minimal"
    assert agent.name == "YAML Minimal"
    assert "buy low" in agent.philosophy
    # system_prompt is a string and contains the persona name
    prompt = agent.get_system_prompt()
    assert "YAML Minimal" in prompt
    # analyze() should return a populated AgentResponse (factors non-empty)
    from augur.personas.base import MarketContext, AgentResponse
    ctx = MarketContext(ticker="AAPL", price=100.0)
    resp = agent.analyze(ctx)
    assert isinstance(resp, AgentResponse)
    assert resp.agent_id == "yaml_minimal"
    assert "momentum" in resp.metadata["factors"]


def test_load_personas_from_dir_loads_multiple(tmp_path):
    """load_personas_from_dir returns one agent per .yaml file (skips failures)."""
    good1 = tmp_path / "p1.yaml"
    good1.write_text(
        "agent_id: dir_one\nname: One\nscoring_weights: {a: 1.0}\n",
        encoding="utf-8",
    )
    good2 = tmp_path / "p2.yml"
    good2.write_text(
        "agent_id: dir_two\nname: Two\nscoring_weights: {a: 1.0}\n",
        encoding="utf-8",
    )
    bad = tmp_path / "bad.yml"
    bad.write_text("not_valid: [", encoding="utf-8")  # will fail to load
    agents = load_personas_from_dir(tmp_path)
    ids = {a.agent_id for a in agents}
    assert {"dir_one", "dir_two"}.issubset(ids)
    # Broken file should be skipped, not raise
    assert all(isinstance(a, YamlAgent) for a in agents)


def test_compute_factor_rejects_bool_base(tmp_path):
    """Boolean YAML base scores must not become 1.0 via float(True)."""
    from augur.persona_loader import _compute_factor
    from augur.personas.base import MarketContext

    ctx = MarketContext(ticker="TEST")
    score = _compute_factor({"base": True, "rules": []}, ctx)
    assert score == 5.0
