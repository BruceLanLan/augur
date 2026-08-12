# -*- coding: utf-8 -*-
"""
Provider Health Dashboard (G08) — track data source connectivity and freshness.

Monitors each registered data provider for latency, success rate, and
coverage. Stores results in get_data_dir()/provider_health.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from augur.data_dir import get_data_dir


@dataclass
class ProviderHealth:
    """Health metrics for a single data provider."""

    provider_name: str
    last_checked: str = ""
    last_success: str = ""
    last_error: str = ""
    success_rate_7d: float = 1.0    # 0.0-1.0
    avg_latency_ms: float = 0
    total_checks: int = 0
    total_successes: int = 0
    total_failures: int = 0
    coverage_tickers: int = 0
    status: str = "unknown"  # "healthy" | "degraded" | "down"


@dataclass
class ProviderHealthDashboard:
    """Aggregate health view across all providers."""

    providers: List[ProviderHealth] = field(default_factory=list)
    generated_at: str = ""

    @property
    def healthy_count(self) -> int:
        return sum(1 for p in self.providers if p.status == "healthy")

    @property
    def degraded_count(self) -> int:
        return sum(1 for p in self.providers if p.status == "degraded")

    @property
    def down_count(self) -> int:
        return sum(1 for p in self.providers if p.status == "down")


class ProviderHealthTracker:
    """Track and report provider health over time.

    Stores a rolling 7-day window of check results per provider.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self._path = storage_path or (get_data_dir() / "provider_health.json")
        self._providers: Dict[str, ProviderHealth] = {}
        self._load()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_success(
        self, provider_name: str, latency_ms: float, tickers: int = 1
    ) -> None:
        """Record a successful provider call."""
        ph = self._get_or_create(provider_name)
        now = datetime.now(timezone.utc).isoformat()
        ph.last_checked = now
        ph.last_success = now
        ph.total_checks += 1
        ph.total_successes += 1
        if ph.total_successes == 1:
            ph.avg_latency_ms = latency_ms
        else:
            ph.avg_latency_ms = (
                ph.avg_latency_ms * (ph.total_successes - 1) + latency_ms
            ) / ph.total_successes
        ph.coverage_tickers = max(ph.coverage_tickers, tickers)
        ph.status = "healthy" if ph.success_rate_7d >= 0.95 else "degraded"
        self._save()

    def record_failure(self, provider_name: str, error_msg: str) -> None:
        """Record a failed provider call."""
        ph = self._get_or_create(provider_name)
        now = datetime.now(timezone.utc).isoformat()
        ph.last_checked = now
        ph.last_error = error_msg
        ph.total_checks += 1
        ph.total_failures += 1
        if ph.total_checks > 0:
            ph.success_rate_7d = ph.total_successes / ph.total_checks
        ph.status = (
            "down" if ph.success_rate_7d < 0.5
            else "degraded" if ph.success_rate_7d < 0.95
            else "healthy"
        )
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_health(self, provider_name: str) -> Optional[ProviderHealth]:
        return self._providers.get(provider_name)

    def get_dashboard(self) -> ProviderHealthDashboard:
        """Return aggregate health dashboard."""
        return ProviderHealthDashboard(
            providers=list(self._providers.values()),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_issues(self) -> List[ProviderHealth]:
        """Return providers that are degraded or down."""
        return [
            p for p in self._providers.values()
            if p.status in ("degraded", "down")
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _get_or_create(self, name: str) -> ProviderHealth:
        if name not in self._providers:
            self._providers[name] = ProviderHealth(provider_name=name)
        return self._providers[name]

    def _save(self) -> None:
        data = {
            name: {
                "provider_name": ph.provider_name,
                "last_checked": ph.last_checked,
                "last_success": ph.last_success,
                "last_error": ph.last_error,
                "success_rate_7d": ph.success_rate_7d,
                "avg_latency_ms": ph.avg_latency_ms,
                "total_checks": ph.total_checks,
                "total_successes": ph.total_successes,
                "total_failures": ph.total_failures,
                "coverage_tickers": ph.coverage_tickers,
                "status": ph.status,
            }
            for name, ph in self._providers.items()
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for name, d in raw.items():
                self._providers[name] = ProviderHealth(
                    provider_name=d.get("provider_name", name),
                    last_checked=d.get("last_checked", ""),
                    last_success=d.get("last_success", ""),
                    last_error=d.get("last_error", ""),
                    success_rate_7d=d.get("success_rate_7d", 1.0),
                    avg_latency_ms=d.get("avg_latency_ms", 0),
                    total_checks=d.get("total_checks", 0),
                    total_successes=d.get("total_successes", 0),
                    total_failures=d.get("total_failures", 0),
                    coverage_tickers=d.get("coverage_tickers", 0),
                    status=d.get("status", "unknown"),
                )
        except (json.JSONDecodeError, OSError):
            self._providers = {}


# Singleton
_tracker: Optional[ProviderHealthTracker] = None


def get_provider_health_tracker() -> ProviderHealthTracker:
    global _tracker
    if _tracker is None:
        _tracker = ProviderHealthTracker()
    return _tracker
