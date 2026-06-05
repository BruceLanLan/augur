# -*- coding: utf-8 -*-
"""Factual audit of persona .md docs (Round 11 Agent A).

These tests guard against the most common factual errors creeping into
docs/knowledge/personas/*.md. They are *content* checks against the docs,
not behavioural tests of any runtime code, so they live in a separate file
so they can be skipped cheaply if needed.

Issues covered (Round 11 audit):

1. buffett.md: must NOT claim Berkshire "bought CRCL" in 2025 -- the
   unverified/forward-looking CRCL line was removed. Crypto posture is
   "still cautious" only.
2. peter-lynch.md: Stalwart example tickers must reflect the actual
   examples Lynch cited (PEP, WBA, MCD, KMB) -- the old list mixed in
   KO/PG/JNJ which are more Buffett stalwarts.
3. li-lu.md: BYD "returns >100x" / ">60x" claims are factually wrong --
   BYD H-shares went from HKD ~8 in 2008 to HKD 250-300 by 2025 (~30-50x
   current; ~47x peak). The doc must reflect the realistic range.
"""

import pathlib

import pytest

PERSONAS_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs" / "knowledge" / "personas"


def _read(name: str) -> str:
    p = PERSONAS_DIR / name
    if not p.exists():
        pytest.skip(f"persona doc {name} not present in this checkout")
    return p.read_text(encoding="utf-8")


# ---------- buffett.md ----------------------------------------------------

class TestBuffettCryptoPosture:
    def test_no_unverified_crcl_claim(self):
        """Berkshire has not confirmed a CRCL position via 13F; the doc must
        not assert one as if it were a historical fact."""
        text = _read("buffett.md")
        # The 'rejected crypto' row should not mention a CRCL buy.
        assert "买入CRCL" not in text, (
            "buffett.md still asserts a 2025 Berkshire CRCL buy "
            "which is not supported by any 13F filing."
        )
        assert "建仓CRCL" not in text, (
            "buffett.md timeline still lists a 2025 'build CRCL' event."
        )

    def test_crypto_row_preserves_disapproval(self):
        """Removing the CRCL claim must not accidentally delete the famous
        Bitcoin 'rat poison' line -- that's a real, well-sourced Buffett quote."""
        text = _read("buffett.md")
        assert "老鼠药" in text, "buffett's well-known 'rat poison' quote is missing"
        assert "比特币" in text, "Bitcoin reference missing from crypto row"


# ---------- peter-lynch.md -----------------------------------------------

class TestLynchStalwartTickers:
    def test_stalwart_section_uses_lynch_canonical_tickers(self):
        """The Stalwarts row must use tickers Lynch actually cited in
        'One Up on Wall Street' / 'Beating the Street', not the generic
        Buffett-style list (KO, PG, JNJ)."""
        text = _read("peter-lynch.md")
        # New canonical set
        for ticker in ("PEP", "WBA", "MCD", "KMB"):
            assert ticker in text, (
                f"peter-lynch.md Stalwarts row missing Lynch-canonical ticker {ticker}"
            )
        # Old inaccurate set must be gone
        for wrong in ("KO, PG, MCD, JNJ", "KO, PG", "JNJ"):
            assert wrong not in text, (
                f"peter-lynch.md still contains incorrect stalwart list fragment: {wrong!r}"
            )


# ---------- li-lu.md ------------------------------------------------------

class TestLiLuBYDReturns:
    def test_no_100x_or_60x_byd_claim(self):
        """BYD returns are ~30-50x (current) / ~47x (peak), not 100x or 60x."""
        text = _read("li-lu.md")
        # These phrasings are the unverified/hallucinated ones
        assert "回报超100倍" not in text, (
            "li-lu.md still claims BYD returned 'over 100x' -- actual is ~30-50x."
        )
        assert "回报超60倍" not in text, (
            "li-lu.md still claims Berkshire BYD 'over 60x' -- actual is ~30-47x."
        )
        assert "后回报超60倍" not in text, (
            "li-lu.md still contains the old 'Berkshire BYD 60x' wording."
        )

    def test_byd_figure_is_in_realistic_range(self):
        """The corrected section must use the realistic 30-50x range
        and the canonical HKD 8 -> HKD 250-300 framing."""
        text = _read("li-lu.md")
        assert "30-50倍" in text, (
            "li-lu.md should now state BYD returned '30-50x' (current range)."
        )
        assert "HKD 8" in text and "HKD 250-300" in text, (
            "li-lu.md should cite the actual BYD entry/exit price band."
        )
