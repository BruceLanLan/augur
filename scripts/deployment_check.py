#!/usr/bin/env python3
"""Deployment readiness check — verify a self-hosted Augur install (H04)."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Tuple


def run_deployment_check() -> Tuple[bool, List[str]]:
    """Check deployment prerequisites.

    Returns (all_ok, messages) where messages describe issues found.
    """
    issues: List[str] = []
    ok: List[str] = []

    # 1. Data dir writable
    from augur.data_dir import get_data_dir
    data_dir = get_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".write_probe"
        probe.write_text("ok")
        probe.unlink()
        ok.append(f"data dir writable: {data_dir}")
    except OSError:
        issues.append(f"data dir NOT writable: {data_dir}")

    # 2. Version import
    import augur
    ok.append(f"augur version: {augur.__version__}")

    # 3. Schemas importable
    from augur.schemas import EvidenceItem, Claim, RunBundle
    ok.append("schemas importable")

    # 4. Dashboard templates exist
    import dashboard.app as dapp
    tpl_dir = dapp.TEMPLATES_DIR
    if tpl_dir and tpl_dir.exists():
        count = len(list(tpl_dir.glob("*.html")))
        ok.append(f"dashboard templates: {count} files")
    else:
        issues.append("dashboard templates missing")

    return (len(issues) == 0, ok + issues)


if __name__ == "__main__":
    success, messages = run_deployment_check()
    print("═══ Augur Deployment Check ═══")
    print()
    for m in messages:
        mark = "✅" if not m.startswith(("data dir NOT", "dashboard templates missing")) else "❌"
        print(f"  {mark} {m}")
    print()
    print("PASS" if success else "FAIL — fix issues above")
    sys.exit(0 if success else 1)
