# -*- coding: utf-8 -*-
"""
augur.compatibility — Compatibility Badge (G07)

Declarative compatibility tracking for skills and data providers across
augur versions.  Provides:

* **SkillCompatibility** — per-skill version / augur-version / tested matrix.
* **ProviderCompatibility** — per-provider version / status record.
* **CompatibilityMatrix** — query interface over the full registry.
* **generate_badge()** — render a compact SVG badge (or dict) for a skill
  or provider.

All data is static / declarative — no runtime introspection of installed
packages (that layer lives in ``optional_deps``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProviderStatus(str, Enum):
    """Lifecycle status of a data provider integration."""

    STABLE = "stable"
    """Fully supported, tested in CI."""

    BETA = "beta"
    """Available but may have known gaps."""

    DEPRECATED = "deprecated"
    """Still functional but scheduled for removal."""

    EXPERIMENTAL = "experimental"
    """Opt-in only; API may change without notice."""


# ---------------------------------------------------------------------------
# SkillCompatibility
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SkillCompatibility:
    """Compatibility record for a single skill.

    Attributes:
        skill_id: Unique skill identifier (e.g. ``"filing_delta"``).
        version: Skill version string (e.g. ``"1.2.0"``).
        augur_versions: List of augur versions this skill is known to work
            with (e.g. ``["10.15.0", "10.14.0"]``).
        tested: Whether this pairing has been verified in CI.
        notes: Optional free-form notes about known issues.
    """

    skill_id: str
    version: str
    augur_versions: List[str] = field(default_factory=list)
    tested: bool = False
    notes: Optional[str] = None

    def supports(self, augur_version: str) -> bool:
        """Return True when this skill is declared compatible with *augur_version*."""
        return augur_version in self.augur_versions

    def __str__(self) -> str:
        tested_mark = "✓" if self.tested else "?"
        return f"{self.skill_id}@{self.version} ({tested_mark})"


# ---------------------------------------------------------------------------
# ProviderCompatibility
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderCompatibility:
    """Compatibility record for a single data provider.

    Attributes:
        provider: Provider name (e.g. ``"yfinance"``, ``"openbb"``).
        version: Provider / adapter version string.
        status: Lifecycle status (stable / beta / deprecated / experimental).
        augur_versions: List of augur versions known to work.
        tested: Whether this pairing has been verified in CI.
        notes: Optional free-form notes.
    """

    provider: str
    version: str
    status: ProviderStatus = ProviderStatus.STABLE
    augur_versions: List[str] = field(default_factory=list)
    tested: bool = False
    notes: Optional[str] = None

    def supports(self, augur_version: str) -> bool:
        """Return True when this provider is declared compatible with *augur_version*."""
        return augur_version in self.augur_versions

    def __str__(self) -> str:
        return f"{self.provider}@{self.version} [{self.status.value}]"


# ---------------------------------------------------------------------------
# CompatibilityMatrix
# ---------------------------------------------------------------------------

@dataclass
class CompatibilityMatrix:
    """Query interface for the full skill + provider compatibility registry.

    Usage::

        matrix = CompatibilityMatrix()
        matrix.register_skill(SkillCompatibility(...))
        matrix.register_provider(ProviderCompatibility(...))

        compat = matrix.skills_for_version("10.15.0")
        badge  = matrix.generate_badge("filing_delta")
    """

    _skills: Dict[str, SkillCompatibility] = field(default_factory=dict)
    _providers: Dict[str, ProviderCompatibility] = field(default_factory=dict)

    # -- registration --------------------------------------------------------

    def register_skill(self, skill: SkillCompatibility) -> None:
        """Register (or overwrite) a skill compatibility record."""
        self._skills[skill.skill_id] = skill

    def register_provider(self, provider: ProviderCompatibility) -> None:
        """Register (or overwrite) a provider compatibility record."""
        self._providers[provider.provider] = provider

    # -- query ---------------------------------------------------------------

    def get_skill(self, skill_id: str) -> Optional[SkillCompatibility]:
        """Look up a single skill by id."""
        return self._skills.get(skill_id)

    def get_provider(self, provider: str) -> Optional[ProviderCompatibility]:
        """Look up a single provider by name."""
        return self._providers.get(provider)

    def skills_for_version(self, augur_version: str) -> List[SkillCompatibility]:
        """Return every skill declared compatible with *augur_version*."""
        return [s for s in self._skills.values() if s.supports(augur_version)]

    def providers_for_version(self, augur_version: str) -> List[ProviderCompatibility]:
        """Return every provider declared compatible with *augur_version*."""
        return [p for p in self._providers.values() if p.supports(augur_version)]

    def all_skills(self) -> List[SkillCompatibility]:
        """Return every registered skill."""
        return list(self._skills.values())

    def all_providers(self) -> List[ProviderCompatibility]:
        """Return every registered provider."""
        return list(self._providers.values())

    def providers_by_status(self, status: ProviderStatus) -> List[ProviderCompatibility]:
        """Return providers filtered by lifecycle status."""
        return [p for p in self._providers.values() if p.status == status]

    # -- badge generation ----------------------------------------------------

    def generate_badge(
        self,
        target: Union[str, SkillCompatibility, ProviderCompatibility],
        fmt: str = "svg",
    ) -> Union[str, Dict[str, Any]]:
        """Generate a compatibility badge for a skill or provider.

        Parameters
        ----------
        target:
            A skill id string, provider name string, or a
            SkillCompatibility / ProviderCompatibility instance.
        fmt:
            ``"svg"`` returns an SVG string; ``"dict"`` returns a
            structured dict suitable for JSON serialisation.

        Returns
        -------
        str or dict
            The rendered badge.
        """
        if isinstance(target, SkillCompatibility):
            record: Union[SkillCompatibility, ProviderCompatibility] = target
        elif isinstance(target, ProviderCompatibility):
            record = target
        elif isinstance(target, str):
            # Try skill first, then provider
            record = self._skills.get(target) or self._providers.get(target)  # type: ignore[assignment]
            if record is None:
                raise KeyError(
                    f"No skill or provider named {target!r} registered"
                )
        else:
            raise TypeError(
                f"target must be str, SkillCompatibility, or ProviderCompatibility, "
                f"got {type(target).__name__}"
            )

        if fmt == "dict":
            return _badge_as_dict(record)
        return _badge_as_svg(record)


# ---------------------------------------------------------------------------
# Badge rendering helpers
# ---------------------------------------------------------------------------

_BADGE_COLORS: Dict[str, str] = {
    "stable":       "#31a354",   # green
    "beta":         "#3182bd",   # blue
    "deprecated":   "#e6550d",   # orange
    "experimental": "#756bb1",   # purple
}


def _badge_label(record: Union[SkillCompatibility, ProviderCompatibility]) -> str:
    """Derive a short label for the badge left-hand side."""
    if isinstance(record, SkillCompatibility):
        return "skill"
    return record.status.value


def _badge_value(record: Union[SkillCompatibility, ProviderCompatibility]) -> str:
    """Derive the right-hand-side text for the badge."""
    if isinstance(record, SkillCompatibility):
        return f"{record.skill_id}@{record.version}"
    return f"{record.provider}@{record.version}"


def _badge_color(record: Union[SkillCompatibility, ProviderCompatibility]) -> str:
    """Pick the badge colour."""
    if isinstance(record, ProviderCompatibility):
        return _BADGE_COLORS.get(record.status.value, "#636363")
    # Skills default to blue
    return "#3182bd"


def _badge_as_dict(
    record: Union[SkillCompatibility, ProviderCompatibility],
) -> Dict[str, Any]:
    """Render the compatibility badge as a structured dict."""
    label = _badge_label(record)
    value = _badge_value(record)
    color = _badge_color(record)

    if isinstance(record, SkillCompatibility):
        return {
            "schemaVersion": 1,
            "label": label,
            "message": value,
            "color": color,
            "skillId": record.skill_id,
            "version": record.version,
            "augurVersions": record.augur_versions,
            "tested": record.tested,
            "notes": record.notes,
        }

    return {
        "schemaVersion": 1,
        "label": label,
        "message": value,
        "color": color,
        "provider": record.provider,
        "version": record.version,
        "status": record.status.value,
        "augurVersions": record.augur_versions,
        "tested": record.tested,
        "notes": record.notes,
    }


def _badge_as_svg(
    record: Union[SkillCompatibility, ProviderCompatibility],
) -> str:
    """Render the compatibility badge as a shields.io-style SVG."""
    label = _badge_label(record)
    value = _badge_value(record)
    color = _badge_color(record)

    # Estimate text widths (rough: ~7.2 px per char for 11px DejaVu Sans)
    label_width = max(40, int(len(label) * 7.2) + 10)
    value_width = max(50, int(len(value) * 7.2) + 10)
    total_width = label_width + value_width
    height = 20

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_width}" height="{height}" role="img" '
        f'aria-label="{label}: {value}">'
        f'<linearGradient id="s" x2="0" y2="100%">'
        f'<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        f'<stop offset="1" stop-opacity=".1"/>'
        f"</linearGradient>"
        f'<clipPath id="r">'
        f'<rect width="{total_width}" height="{height}" rx="3" fill="#fff"/>'
        f"</clipPath>"
        f'<g clip-path="url(#r)">'
        f'<rect width="{label_width}" height="{height}" fill="#555"/>'
        f'<rect x="{label_width}" width="{value_width}" height="{height}" '
        f'fill="{color}"/>'
        f'<rect width="{total_width}" height="{height}" fill="url(#s)"/>'
        f"</g>"
        f'<g fill="#fff" text-anchor="middle" '
        f'font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">'
        f'<text x="{label_width // 2}" y="14">{label}</text>'
        f'<text x="{label_width + value_width // 2}" y="14">{value}</text>'
        f"</g>"
        f"</svg>"
    )
    return svg


# ---------------------------------------------------------------------------
# Module-level convenience: generate_badge without a matrix instance
# ---------------------------------------------------------------------------

def generate_badge(
    skill_or_provider: Union[SkillCompatibility, ProviderCompatibility],
    fmt: str = "svg",
) -> Union[str, Dict[str, Any]]:
    """Render a compatibility badge directly from a record.

    This is the standalone entrypoint — no ``CompatibilityMatrix`` needed
    when you already have a ``SkillCompatibility`` or
    ``ProviderCompatibility`` instance.

    Parameters
    ----------
    skill_or_provider:
        The compatibility record.
    fmt:
        ``"svg"`` or ``"dict"``.

    Returns
    -------
    str or dict
    """
    if fmt == "dict":
        return _badge_as_dict(skill_or_provider)
    return _badge_as_svg(skill_or_provider)
