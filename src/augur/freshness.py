
"""Data Freshness Tracker — check staleness of cached data (data pipeline)."""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from augur.data_dir import get_data_dir

@dataclass
class FreshnessRecord:
    key: str
    last_updated: str
    max_age_hours: float = 24.0
    is_stale: bool = False
    age_hours: float = 0.0

class FreshnessTracker:
    def __init__(self, path: Path = None):
        self._path = path or (get_data_dir() / "freshness.json")
        self._records: Dict[str, FreshnessRecord] = {}
        self._load()

    def touch(self, key: str, max_age_hours: float = 24.0) -> FreshnessRecord:
        now = datetime.now(timezone.utc).isoformat()
        r = FreshnessRecord(key=key, last_updated=now, max_age_hours=max_age_hours)
        self._records[key] = r
        self._save()
        return r

    def check(self, key: str) -> Optional[FreshnessRecord]:
        r = self._records.get(key)
        if not r:
            return None
        try:
            ts = datetime.fromisoformat(r.last_updated)
            age = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            r.age_hours = round(age, 2)
            r.is_stale = age > r.max_age_hours
        except ValueError:
            r.is_stale = True
        return r

    def list_stale(self) -> List[FreshnessRecord]:
        return [r for k in self._records for r in [self.check(k)] if r and r.is_stale]

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({k: {"key": v.key, "last_updated": v.last_updated, "max_age_hours": v.max_age_hours} for k, v in self._records.items()}, indent=2), encoding="utf-8")

    def _load(self):
        if not self._path.exists():
            return
        try:
            for k, v in json.loads(self._path.read_text(encoding="utf-8")).items():
                self._records[k] = FreshnessRecord(key=v.get("key", k), last_updated=v.get("last_updated", ""), max_age_hours=v.get("max_age_hours", 24.0))
        except (json.JSONDecodeError, OSError):
            self._records = {}
