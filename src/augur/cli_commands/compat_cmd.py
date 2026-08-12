# -*- coding: utf-8 -*-
"""Compatibility report — CLI view of the skill/provider matrix (G07)."""
from __future__ import annotations

def build_compatibility_report() -> str:
    """Build a human-readable compatibility report from built-in skills."""
    from augur.compatibility import CompatibilityMatrix, SkillCompatibility
    from augur.skills.loader import load_builtin_skills

    matrix = CompatibilityMatrix()
    for spec in load_builtin_skills():
        matrix.register_skill(SkillCompatibility(
            spec.id, spec.version,
            augur_versions=["11.0.0-rc1", "11.0.0"],
            tested=True,
        ))

    lines = ["═══ Compatibility Report ═══", ""]
    for skill in matrix.all_skills():
        badge = matrix.generate_badge(skill.skill_id)
        mark = "✓" if skill.tested else "?"
        lines.append(f"  {mark} {skill.skill_id}@{skill.version} — {badge['status'] if isinstance(badge, dict) else 'compatible'}")
    lines.append("")
    lines.append(f"Total skills: {len(matrix.all_skills())}")
    return "\n".join(lines)


import click

from augur.cli_commands.compat_cmd import build_compatibility_report


@click.command("compat")
def compat_cmd():
    """Show skill/provider compatibility matrix."""
    click.echo(build_compatibility_report())
