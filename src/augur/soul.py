# -*- coding: utf-8 -*-
"""
Soul Injector - 将 Augur 投资人人格注入到 Hermes Profile 或任意 Agent 系统

Usage:
    augur inject-soul --profile my-buffett --persona buffett
    augur inject-soul --profile china-value --persona duan_yongping
"""

from pathlib import Path
from typing import Optional

from augur.registry import AgentRegistry


# Persona ID -> markdown filename mapping
_PERSONA_MD_MAP = {
    "buffett": "buffett.md",
    "graham": "graham.md",
    "lynch": "peter-lynch.md",
    "dalio": "ray-dalio.md",
    "munger": "munger.md",
    "soros": "george-soros.md",
    "marks": "howard-marks.md",
    "cathie_wood": "cathie-wood.md",
    "fisher": "philip-fisher.md",
    "arps": "arps-crypto-gold.md",
    "aschenbrenner": "leopold-aschenbrenner.md",
    "dayu": "da-yu.md",
    "thiel": "thiel.md",
    "duan_yongping": "duan-yongping.md",
    "zhang_lei": "zhang-lei.md",
    "li_lu": "li-lu.md",
    "dan_bin": "dan-bin.md",
    "serenity": "serenity.md",
}


def _find_personas_dir() -> Optional[Path]:
    """Locate the personas/ directory."""
    candidates = [
        Path(__file__).parent.parent.parent / "personas",
        Path.cwd() / "personas",
    ]
    for d in candidates:
        if d.exists():
            return d
    return None


def _load_persona_md(persona_id: str) -> str:
    """Load the full markdown document for a persona."""
    personas_dir = _find_personas_dir()
    if not personas_dir:
        return ""

    filename = _PERSONA_MD_MAP.get(persona_id)
    if not filename:
        # Try direct lookup
        filename = f"{persona_id}.md"

    md_path = personas_dir / filename
    if md_path.exists():
        return md_path.read_text(encoding="utf-8")
    return ""


def generate_soul(persona_id: str) -> str:
    """
    Generate the full system prompt (soul) for a persona.

    Combines:
    1. The persona's system prompt from get_system_prompt()
    2. The full persona .md document content
    3. The persona's scoring rules and key metrics
    """
    registry = AgentRegistry()
    agent = registry.get(persona_id)
    if not agent:
        raise ValueError(f"Persona '{persona_id}' not found. Available: {', '.join(a.agent_id for a in registry.get_all())}")

    # Part 1: System prompt
    system_prompt = agent.get_system_prompt()

    # Part 2: Persona markdown document
    persona_md = _load_persona_md(persona_id)

    # Part 3: Scoring rules and key metrics
    scoring_section = _build_scoring_section(agent)

    # Combine all parts
    parts = [
        f"# {agent.name} - Soul Definition\n",
        "## System Prompt\n",
        system_prompt,
        "",
    ]

    if persona_md:
        parts.extend([
            "## Persona Document\n",
            persona_md,
            "",
        ])

    parts.extend([
        "## Scoring Rules & Key Metrics\n",
        scoring_section,
    ])

    return "\n".join(parts)


def _build_scoring_section(agent) -> str:
    """Build the scoring rules section from agent attributes."""
    lines = []

    # Scoring weights
    if agent.scoring_weights:
        lines.append("### Factor Weights\n")
        for factor, weight in agent.scoring_weights.items():
            lines.append(f"- **{factor}**: {weight:.0%}")
        lines.append("")

    # Thresholds
    if agent.thresholds:
        lines.append("### Decision Thresholds\n")
        for key, value in agent.thresholds.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    # Philosophy
    if agent.philosophy:
        lines.append("### Core Philosophy\n")
        for p in agent.philosophy:
            lines.append(f"- {p}")
        lines.append("")

    return "\n".join(lines)


def inject_soul(profile_path: str, persona_id: str, format: str = "hermes", output_dir: str = None) -> Path:
    """
    Inject soul into a profile config file.

    Args:
        profile_path: Profile name or path
        persona_id: The persona to inject
        format: Output format - 'hermes', 'claude', or 'raw'
        output_dir: Optional output directory (defaults to current dir)

    Returns:
        Path to the generated file
    """
    soul_content = generate_soul(persona_id)

    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    if format == "hermes":
        # For Hermes format: write to profile_path/soul.md
        profile_dir = out_dir / profile_path
        profile_dir.mkdir(parents=True, exist_ok=True)
        output_file = profile_dir / "soul.md"
        output_file.write_text(soul_content, encoding="utf-8")
        return output_file

    elif format == "claude":
        # For Claude format: write as a system prompt JSON snippet
        import json
        claude_config = {
            "name": profile_path,
            "persona_id": persona_id,
            "system_prompt": soul_content,
        }
        output_file = out_dir / f"{profile_path}-claude.json"
        output_file.write_text(json.dumps(claude_config, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_file

    else:
        # Raw format: just the soul markdown
        output_file = out_dir / f"{profile_path}-soul.md"
        output_file.write_text(soul_content, encoding="utf-8")
        return output_file


def inject_all_souls(profiles_dir: str, persona_mapping: dict, format: str = "hermes") -> list:
    """
    Batch inject multiple personas into multiple profiles.

    Args:
        profiles_dir: Directory for all profile outputs
        persona_mapping: Dict of {profile_name: persona_id}
        format: Output format

    Returns:
        List of generated file paths
    """
    results = []
    for profile_name, persona_id in persona_mapping.items():
        try:
            path = inject_soul(profile_name, persona_id, format=format, output_dir=profiles_dir)
            results.append(path)
        except Exception as e:
            results.append(f"ERROR: {profile_name}/{persona_id}: {e}")
    return results


class SoulInjector:
    """Soul injection engine - convenience class wrapping module functions."""

    def __init__(self):
        self._initialized = True

    def inject(self, agent_id: str, soul_config: dict = None):
        """Inject soul into a persona profile."""
        profile = soul_config.get("profile", agent_id) if soul_config else agent_id
        fmt = soul_config.get("format", "hermes") if soul_config else "hermes"
        output_dir = soul_config.get("output_dir") if soul_config else None
        return inject_soul(profile, agent_id, format=fmt, output_dir=output_dir)

    def configure(self, config: dict):
        """Configure the soul injector."""
        pass

    def generate(self, persona_id: str) -> str:
        """Generate soul content for a persona."""
        return generate_soul(persona_id)
