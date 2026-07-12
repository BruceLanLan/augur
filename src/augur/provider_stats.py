# -*- coding: utf-8 -*-
"""
augur.provider_stats - Lightweight local history for `augur doctor`'s
data-source connectivity checks.

Each `augur doctor` run (without --offline) records that day's per-provider
reachable/failed outcome to a small local JSON file (default
~/.augur/provider_stats.json), pruned to a rolling window. This turns
one-shot probes into a short trend so a dead endpoint (e.g. stooq's 404s,
found by hand in commit 24c8609) would show up as "0/5 reachable this week"
instead of requiring someone to notice by accident.

Deliberately scoped to `augur doctor` invocations only, not the live
analyze()/consensus data-fetch path -- this is an on-demand diagnostic
history, not production telemetry, so it never adds I/O to the hot path
and never risks writing to a real user's ~/.augur during an unrelated
test run of the data layer.

Never raises: a failure to record or read history must never break the
diagnostic command it supports.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

RETENTION_DAYS = 7
_lock = threading.Lock()


def _default_path() -> Path:
    augur_dir = Path.home() / ".augur"
    augur_dir.mkdir(parents=True, exist_ok=True)
    return augur_dir / "provider_stats.json"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load(path: Path) -> Dict[str, Dict[str, Dict[str, int]]]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _prune(data: Dict[str, Dict[str, Dict[str, int]]]) -> Dict[str, Dict[str, Dict[str, int]]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    pruned: Dict[str, Dict[str, Dict[str, int]]] = {}
    for provider, days in data.items():
        kept = {day: counts for day, counts in days.items() if day >= cutoff}
        if kept:
            pruned[provider] = kept
    return pruned


def record(provider_name: str, ok: bool, path: Optional[Path] = None) -> None:
    """Record one `augur doctor` connectivity probe outcome. Never raises."""
    try:
        target = path or _default_path()
        with _lock:
            data = _load(target)
            day = _today()
            bucket = data.setdefault(provider_name, {}).setdefault(day, {"ok": 0, "fail": 0})
            bucket["ok" if ok else "fail"] += 1
            data = _prune(data)
            target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("provider_stats.record failed (non-fatal)", exc_info=True)


def summary(path: Optional[Path] = None) -> Dict[str, Dict[str, int]]:
    """Return {provider: {"ok": n, "fail": n}} aggregated over the retention window."""
    try:
        target = path or _default_path()
        return {
            provider: {
                "ok": sum(d.get("ok", 0) for d in days.values()),
                "fail": sum(d.get("fail", 0) for d in days.values()),
            }
            for provider, days in _prune(_load(target)).items()
        }
    except Exception:
        logger.debug("provider_stats.summary failed (non-fatal)", exc_info=True)
        return {}
