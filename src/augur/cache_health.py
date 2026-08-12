
"""Cache freshness integration — connect FreshnessTracker to EDGAR cache.

Usage::
    from augur.cache_health import check_edgar_cache_freshness
    stale = check_edgar_cache_freshness()  # List[(ticker, age_hours)]
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from augur.data_dir import get_data_dir

# Default max age for EDGAR companyfacts cache (7 days for annual data)
_DEFAULT_MAX_AGE_HOURS = 24 * 7


def check_edgar_cache_freshness(
    max_age_hours: float = _DEFAULT_MAX_AGE_HOURS,
) -> List[Tuple[str, float]]:
    """Check EDGAR cache staleness.

    Returns:
        List of (ticker, age_hours) for stale cached files.
    """
    cache_dir = get_data_dir() / "edgar_cache"
    if not cache_dir.exists():
        return []

    stale: List[Tuple[str, float]] = []
    now = datetime.now(timezone.utc)
    for f in cache_dir.glob("*.json"):
        try:
            ticker = f.stem.split("_")[0].upper()
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            age_hours = (now - mtime).total_seconds() / 3600
            if age_hours > max_age_hours:
                stale.append((ticker, round(age_hours, 1)))
        except (OSError, ValueError, IndexError):
            continue
    return sorted(stale, key=lambda x: -x[1])


def cache_size_report() -> dict:
    """Report EDGAR cache size and file count."""
    cache_dir = get_data_dir() / "edgar_cache"
    if not cache_dir.exists():
        return {"exists": False, "files": 0, "size_bytes": 0}
    files = list(cache_dir.glob("*.json"))
    total = sum(f.stat().st_size for f in files)
    return {
        "exists": True,
        "files": len(files),
        "size_bytes": total,
        "size_mb": round(total / 1024 / 1024, 2),
    }
