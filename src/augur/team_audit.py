
"""Team Audit (H05) — action logging for small-team accountability."""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from augur.data_dir import get_data_dir

@dataclass
class AuditEntry:
    audit_id: str; action: str; user: str = "local"
    ticker: str = ""; details: dict = field(default_factory=dict)
    created_at: str = ""

class AuditLog:
    def __init__(self, path: Path = None):
        self._path = path or (get_data_dir() / "audit_log.json")
        self._entries: List[AuditEntry] = []; self._load()

    def log(self, action: str, user: str = "local", ticker: str = "", details: dict = None) -> AuditEntry:
        import hashlib, time
        e = AuditEntry(
            audit_id=f"au_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}",
            action=action, user=user, ticker=ticker.upper() if ticker else "",
            details=details or {}, created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._entries.append(e)
        if len(self._entries) > 10000: self._entries = self._entries[-5000:]
        self._save(); return e

    def list_by_user(self, user: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.user == user]

    def list_by_action(self, action: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.action == action]

    def recent(self, limit: int = 20) -> List[AuditEntry]:
        return self._entries[-limit:]

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([{
            "audit_id": e.audit_id, "action": e.action, "user": e.user,
            "ticker": e.ticker, "details": e.details, "created_at": e.created_at,
        } for e in self._entries], indent=2, default=str), encoding="utf-8")

    def _load(self):
        if not self._path.exists(): return
        try:
            for d in json.loads(self._path.read_text(encoding="utf-8")):
                self._entries.append(AuditEntry(
                    audit_id=d.get("audit_id",""), action=d.get("action",""), user=d.get("user","local"),
                    ticker=d.get("ticker",""), details=d.get("details",{}), created_at=d.get("created_at",""),
                ))
        except: self._entries = []
