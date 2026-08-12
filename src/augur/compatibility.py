# -*- coding: utf-8 -*-
"""Compatibility Badge system (G07) — track skill/provider compatibility matrix."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SkillCompatibility:
    skill_id: str; version: str
    augur_versions: List[str]  # e.g. [">=11,<12"]
    tested_on: List[str]       # e.g. ["11.0.0"]
    status: str = "compatible"  # compatible | untested | incompatible


@dataclass
class ProviderCompatibility:
    provider: str; version: str = ""
    status: str = "unknown"
    last_tested: str = ""; notes: str = ""


@dataclass
class CompatibilityMatrix:
    skills: List[SkillCompatibility] = field(default_factory=list)
    providers: List[ProviderCompatibility] = field(default_factory=list)

    def check_skill(self, skill_id: str, augur_version: str) -> str:
        for s in self.skills:
            if s.skill_id == skill_id:
                for constraint in s.augur_versions:
                    if _version_matches(augur_version, constraint):
                        return s.status
        return "untested"

    def to_dict(self) -> dict:
        return {
            "skills": [
                {"id": s.skill_id, "version": s.version, "status": s.status}
                for s in self.skills
            ],
            "providers": [
                {"provider": p.provider, "status": p.status}
                for p in self.providers
            ],
        }


def _version_matches(version: str, constraint: str) -> bool:
    """Simple semver constraint check (>=x,<y format)."""
    try:
        parts = version.replace("rc", ".").split(".")
        v = tuple(int(p) for p in parts[:2] if p.isdigit())
        if ">=" in constraint and "<" in constraint:
            lo = constraint.split(">=")[1].split("<")[0].strip().rstrip(",")
            hi = constraint.split("<")[1].strip()
            lo_v = tuple(int(p) for p in lo.split(".")[:2])
            hi_v = tuple(int(p) for p in hi.split(".")[:2])
            return lo_v <= v < hi_v
    except (ValueError, IndexError):
        pass
    return False


def generate_badge(skill_id: str, status: str) -> dict:
    """Generate badge metadata for a skill."""
    colors = {"compatible": "brightgreen", "untested": "lightgrey", "incompatible": "red"}
    return {
        "schemaVersion": 1,
        "label": skill_id,
        "message": status,
        "color": colors.get(status, "lightgrey"),
    }
