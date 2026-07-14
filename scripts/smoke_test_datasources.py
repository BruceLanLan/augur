#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/smoke_test_datasources.py - Real-network data-source smoke test.

Run weekly by .github/workflows/data-source-smoke.yml (and on-demand via
workflow_dispatch) to catch third-party data source breakage automatically
instead of requiring a human to notice by accident -- the way stooq's dead
/q/l/ and /q/d/l/ endpoints were found (commit 24c8609, documented after
the fact in src/augur/datasources/stooq_provider.py).

Two independent checks, deliberately given different severity:

  - EDGAR (SEC): a real CIK lookup + company-facts fetch for AAPL. SEC
    rarely blocks or rate-limits CI runner IPs, so a failure here is a
    meaningful signal -- this check's exit code is load-bearing (job fails).
  - yfinance: a real quote fetch for AAPL. Yahoo Finance frequently
    rate-limits or blocks cloud/CI IP ranges in ways that reflect the
    runner's IP reputation, not a real regression in augur or yfinance
    itself -- this check always reports its result but never fails the job.

Usage:
    python scripts/smoke_test_datasources.py --edgar
    python scripts/smoke_test_datasources.py --yfinance
    python scripts/smoke_test_datasources.py --all
"""

from __future__ import annotations

import argparse
import os
import sys


def check_edgar() -> bool:
    """Real (non-mocked) EDGAR CIK lookup + company-facts fetch for AAPL."""
    from augur.consensus.edgar_fundamentals import EdgarClient

    os.environ.setdefault("AUGUR_EDGAR_CONTACT_EMAIL", "ci-smoke-test@augur-agents.invalid")

    client = EdgarClient()
    cik = client.get_cik("AAPL")
    if not cik:
        print("EDGAR: CIK lookup FAILED for AAPL", file=sys.stderr)
        return False
    print(f"EDGAR: CIK lookup OK -- AAPL -> {cik}")

    facts = client.get_company_facts("AAPL")
    if not facts:
        print("EDGAR: company facts FAILED for AAPL", file=sys.stderr)
        return False
    print("EDGAR: company facts OK -- non-empty response received")
    return True


def check_yfinance() -> bool:
    """Real (non-mocked) yfinance quote fetch for AAPL."""
    from augur.datasources import YFinanceProvider

    try:
        YFinanceProvider().fetch("AAPL")
    except Exception as exc:
        print(f"yfinance: FAILED -- {exc}", file=sys.stderr)
        return False
    print("yfinance: OK -- AAPL reachable")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edgar", action="store_true", help="Run the EDGAR check only")
    parser.add_argument("--yfinance", action="store_true", help="Run the yfinance check only")
    parser.add_argument("--all", action="store_true", help="Run both checks")
    args = parser.parse_args()

    run_edgar = args.edgar or args.all or not (args.edgar or args.yfinance or args.all)
    run_yfinance = args.yfinance or args.all

    edgar_ok = True
    if run_edgar:
        edgar_ok = check_edgar()

    if run_yfinance:
        yfinance_ok = check_yfinance()
        if not yfinance_ok:
            print(
                "::warning::yfinance smoke test failed -- CI runner IPs are "
                "frequently rate-limited/blocked by Yahoo Finance in ways "
                "unrelated to a real regression, so this does not fail the job.",
            )

    return 0 if edgar_ok else 1


if __name__ == "__main__":
    sys.exit(main())
