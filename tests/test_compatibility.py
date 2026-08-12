# -*- coding: utf-8 -*-
"""
Tests for augur.compatibility (G07 — Compatibility Badge).

Covers:
  - SkillCompatibility: creation, supports(), __str__
  - ProviderCompatibility: creation, supports(), __str__, status enum
  - CompatibilityMatrix: registration, query by version, query by status
  - generate_badge: SVG output, dict output for both skill and provider
  - Module-level generate_badge standalone function
"""
from __future__ import annotations

import pytest

from augur.compatibility import (
    CompatibilityMatrix,
    ProviderCompatibility,
    ProviderStatus,
    SkillCompatibility,
    generate_badge,
)


# ---------------------------------------------------------------------------
# SkillCompatibility
# ---------------------------------------------------------------------------

class TestSkillCompatibility:
    """Tests for the SkillCompatibility record."""

    def test_creation_defaults(self):
        """Minimal construction with defaults."""
        sk = SkillCompatibility(skill_id="filing_delta", version="1.2.0")
        assert sk.skill_id == "filing_delta"
        assert sk.version == "1.2.0"
        assert sk.augur_versions == []
        assert sk.tested is False
        assert sk.notes is None

    def test_supports_version(self):
        """supports() returns True only for listed versions."""
        sk = SkillCompatibility(
            skill_id="earnings_prep",
            version="2.0.0",
            augur_versions=["10.15.0", "10.14.0"],
        )
        assert sk.supports("10.15.0") is True
        assert sk.supports("10.14.0") is True
        assert sk.supports("9.0.0") is False

    def test_str_representation(self):
        """__str__ includes id@version and tested marker."""
        sk_untested = SkillCompatibility(skill_id="x", version="1.0")
        assert "?" in str(sk_untested)
        sk_tested = SkillCompatibility(skill_id="y", version="2.0", tested=True)
        assert "✓" in str(sk_tested)


# ---------------------------------------------------------------------------
# ProviderCompatibility
# ---------------------------------------------------------------------------

class TestProviderCompatibility:
    """Tests for the ProviderCompatibility record."""

    def test_creation_defaults(self):
        """Minimal construction with defaults."""
        pc = ProviderCompatibility(provider="yfinance", version="0.2.0")
        assert pc.provider == "yfinance"
        assert pc.version == "0.2.0"
        assert pc.status == ProviderStatus.STABLE
        assert pc.augur_versions == []
        assert pc.tested is False

    def test_custom_status(self):
        """Non-default status is preserved."""
        pc = ProviderCompatibility(
            provider="openbb",
            version="4.0.0",
            status=ProviderStatus.EXPERIMENTAL,
        )
        assert pc.status == ProviderStatus.EXPERIMENTAL

    def test_supports_version(self):
        """supports() works for providers too."""
        pc = ProviderCompatibility(
            provider="finnhub",
            version="1.0.0",
            augur_versions=["10.15.0"],
        )
        assert pc.supports("10.15.0") is True
        assert pc.supports("10.13.0") is False

    def test_str_representation(self):
        """__str__ includes provider@version and status."""
        pc = ProviderCompatibility(
            provider="yfinance", version="0.2.0", status=ProviderStatus.BETA
        )
        s = str(pc)
        assert "yfinance@0.2.0" in s
        assert "beta" in s


# ---------------------------------------------------------------------------
# CompatibilityMatrix
# ---------------------------------------------------------------------------

class TestCompatibilityMatrix:
    """Tests for the CompatibilityMatrix registry and queries."""

    @pytest.fixture
    def populated_matrix(self) -> CompatibilityMatrix:
        """A matrix with a few skills and providers pre-registered."""
        m = CompatibilityMatrix()
        m.register_skill(
            SkillCompatibility(
                skill_id="filing_delta",
                version="1.0.0",
                augur_versions=["10.15.0", "11.0.0"],
                tested=True,
            )
        )
        m.register_skill(
            SkillCompatibility(
                skill_id="earnings_prep",
                version="2.0.0",
                augur_versions=["10.15.0"],
            )
        )
        m.register_provider(
            ProviderCompatibility(
                provider="yfinance",
                version="0.2.0",
                augur_versions=["10.15.0"],
                status=ProviderStatus.STABLE,
                tested=True,
            )
        )
        m.register_provider(
            ProviderCompatibility(
                provider="openbb",
                version="4.0.0",
                augur_versions=["11.0.0"],
                status=ProviderStatus.EXPERIMENTAL,
            )
        )
        return m

    def test_get_skill_found(self, populated_matrix):
        """Lookup by skill id returns the record."""
        sk = populated_matrix.get_skill("filing_delta")
        assert sk is not None
        assert sk.skill_id == "filing_delta"
        assert sk.version == "1.0.0"

    def test_get_skill_not_found(self, populated_matrix):
        """Unknown skill id returns None."""
        assert populated_matrix.get_skill("nonexistent") is None

    def test_get_provider_found(self, populated_matrix):
        """Lookup by provider name returns the record."""
        pc = populated_matrix.get_provider("yfinance")
        assert pc is not None
        assert pc.provider == "yfinance"
        assert pc.status == ProviderStatus.STABLE

    def test_skills_for_version(self, populated_matrix):
        """skills_for_version filters correctly."""
        v10 = populated_matrix.skills_for_version("10.15.0")
        assert len(v10) == 2  # both skills support 10.15.0
        v11 = populated_matrix.skills_for_version("11.0.0")
        assert len(v11) == 1  # only filing_delta

    def test_providers_for_version(self, populated_matrix):
        """providers_for_version filters correctly."""
        v10 = populated_matrix.providers_for_version("10.15.0")
        assert len(v10) == 1  # yfinance
        assert v10[0].provider == "yfinance"
        v11 = populated_matrix.providers_for_version("11.0.0")
        assert len(v11) == 1  # openbb
        assert v11[0].provider == "openbb"

    def test_all_skills_and_providers(self, populated_matrix):
        """all_skills / all_providers return everything registered."""
        assert len(populated_matrix.all_skills()) == 2
        assert len(populated_matrix.all_providers()) == 2

    def test_providers_by_status(self, populated_matrix):
        """Filter providers by lifecycle status."""
        stable = populated_matrix.providers_by_status(ProviderStatus.STABLE)
        assert len(stable) == 1
        assert stable[0].provider == "yfinance"

        exp = populated_matrix.providers_by_status(ProviderStatus.EXPERIMENTAL)
        assert len(exp) == 1
        assert exp[0].provider == "openbb"

        dep = populated_matrix.providers_by_status(ProviderStatus.DEPRECATED)
        assert len(dep) == 0


# ---------------------------------------------------------------------------
# generate_badge (standalone)
# ---------------------------------------------------------------------------

class TestGenerateBadge:
    """Tests for badge generation (SVG and dict)."""

    @pytest.fixture
    def skill(self) -> SkillCompatibility:
        return SkillCompatibility(
            skill_id="earnings_prep",
            version="2.0.0",
            augur_versions=["10.15.0"],
            tested=True,
            notes="Needs yfinance ≥ 0.2.0",
        )

    @pytest.fixture
    def provider(self) -> ProviderCompatibility:
        return ProviderCompatibility(
            provider="yfinance",
            version="0.2.0",
            status=ProviderStatus.STABLE,
            augur_versions=["10.15.0"],
            tested=True,
        )

    def test_svg_for_skill(self, skill):
        """generate_badge returns valid SVG for a skill."""
        svg = generate_badge(skill, fmt="svg")
        assert isinstance(svg, str)
        assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
        assert "earnings_prep@2.0.0" in svg
        assert "</svg>" in svg

    def test_svg_for_provider(self, provider):
        """generate_badge returns valid SVG for a provider."""
        svg = generate_badge(provider, fmt="svg")
        assert isinstance(svg, str)
        assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
        assert "yfinance@0.2.0" in svg
        assert "stable" in svg  # the label side
        assert "</svg>" in svg

    def test_dict_for_skill(self, skill):
        """generate_badge returns structured dict for a skill."""
        d = generate_badge(skill, fmt="dict")
        assert isinstance(d, dict)
        assert d["schemaVersion"] == 1
        assert d["skillId"] == "earnings_prep"
        assert d["version"] == "2.0.0"
        assert d["tested"] is True
        assert d["notes"] == "Needs yfinance ≥ 0.2.0"

    def test_dict_for_provider(self, provider):
        """generate_badge returns structured dict for a provider."""
        d = generate_badge(provider, fmt="dict")
        assert isinstance(d, dict)
        assert d["provider"] == "yfinance"
        assert d["status"] == "stable"
        assert d["tested"] is True

    def test_default_fmt_is_svg(self, skill):
        """Default format is SVG."""
        result = generate_badge(skill)
        assert isinstance(result, str)
        assert result.startswith("<svg")

    def test_matrix_generate_badge_by_string(self):
        """CompatibilityMatrix.generate_badge resolves string targets."""
        m = CompatibilityMatrix()
        m.register_skill(
            SkillCompatibility(
                skill_id="filing_delta",
                version="1.0",
                augur_versions=["10.15.0"],
            )
        )
        svg = m.generate_badge("filing_delta", fmt="svg")
        assert "filing_delta@1.0" in svg

    def test_matrix_generate_badge_unknown_raises(self):
        """Unknown string target raises KeyError."""
        m = CompatibilityMatrix()
        with pytest.raises(KeyError, match="no_skill_here"):
            m.generate_badge("no_skill_here")

    def test_matrix_generate_badge_rejects_bad_type(self):
        """Non-string, non-record target raises TypeError."""
        m = CompatibilityMatrix()
        with pytest.raises(TypeError):
            m.generate_badge(42)  # type: ignore[arg-type]
