# -*- coding: utf-8 -*-
"""Shared ticker universe and date window for this project's real-data
research scripts (regime_weight_oos.py, generate_agent_correlation.py,
factor_attribution.py, generate_rolling_ic.py).

Extracted 2026-07-16 after a code review found the same 37-ticker list and
2022-01..2026-06 window duplicated byte-for-byte across four separate
scripts -- a real drift risk, not a hypothetical one: one script's real run
already logged AXP returning 0 records due to a transient yfinance issue,
and a future ticker swap/fix applied to only one copy would make the four
scripts' "same universe" claims in their own docstrings silently false.

Not a library API -- these are constants for scripts to import, matching
the "manual research script, no pytest coverage for main()" convention
this whole family of scripts already follows (see any of the four
callers' own module docstrings for why).
"""

# 37 tickers, cross-sector: mega-cap tech, banks, energy, consumer staples,
# healthcare, industrials. Deliberately not curated to favor any agent style.
UNIVERSE = [
    # Tech / growth
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AMD", "CRM", "ORCL", "ADBE",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP",
    # Energy
    "XOM", "CVX", "COP", "SLB",
    # Consumer staples / retail
    "KO", "PG", "WMT", "COST", "MCD", "PEP",
    # Healthcare
    "JNJ", "PFE", "UNH", "MRK", "ABBV", "LLY",
    # Industrials
    "CAT", "BA", "HON", "GE",
]

START = "2022-01-01"
END = "2026-06-01"
