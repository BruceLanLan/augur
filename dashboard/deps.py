"""Shared dependencies for dashboard route modules.

Provides:
- Jinja2 templates (for HTML rendering without circular imports)
- AgentRegistry / DecisionCoordinator singletons (lazy, thread-safe)
- Per-ticker rate limiter (_check_rate_limit) and token-bucket rate limiter
- Rules engine singleton (_get_rules_engine)
- I18n helpers (_i18n_context, _load_translations)
- History helper (_save_history_safe)
"""

import json
import threading
import time as _time
from pathlib import Path
from typing import Any, Dict, List, Optional

_APP_START_TIME = _time.time()

try:
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
except ImportError:
    templates = None  # type: ignore[assignment]

from augur.registry import AgentRegistry, DecisionCoordinator

_registry: Optional[AgentRegistry] = None
_coordinator: Optional[DecisionCoordinator] = None
_singleton_init_lock = threading.RLock()


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        with _singleton_init_lock:
            if _registry is None:
                _registry = AgentRegistry()
    return _registry


def get_coordinator() -> DecisionCoordinator:
    global _coordinator
    if _coordinator is None:
        with _singleton_init_lock:
            if _coordinator is None:
                _coordinator = DecisionCoordinator(get_registry())
    return _coordinator


# ============ Per-ticker Rate Limiter ============

_rate_limits: Dict[str, List[float]] = {}
_rate_limit_lock = threading.Lock()
_RATE_LIMIT_MAX = 30
_RATE_LIMIT_WINDOW = 60.0


def _check_rate_limit(ticker: str) -> bool:
    """Check and enforce rate limit for a ticker. Returns True if allowed, False if exceeded."""
    now = _time.time()
    ticker_key = ticker.upper()
    with _rate_limit_lock:
        if ticker_key in _rate_limits:
            _rate_limits[ticker_key] = [
                ts for ts in _rate_limits[ticker_key] if now - ts < _RATE_LIMIT_WINDOW
            ]
        else:
            _rate_limits[ticker_key] = []

        if len(_rate_limits[ticker_key]) >= _RATE_LIMIT_MAX:
            return False

        _rate_limits[ticker_key].append(now)

        if len(_rate_limits) > 1000:
            stale_keys = [
                k for k, v in _rate_limits.items()
                if not v or all(now - ts >= _RATE_LIMIT_WINDOW for ts in v)
            ]
            for k in stale_keys:
                del _rate_limits[k]

        return True


# ============ Token Bucket Rate Limiter ============

class TokenBucket:
    """Thread-safe token-bucket rate limiter."""

    __slots__ = ("capacity", "refill_rate", "tokens", "last_refill", "_lock")

    def __init__(self, capacity: int, refill_rate: float):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_rate < 0:
            raise ValueError("refill_rate must be >= 0")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = _time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = _time.time()
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(
                float(self.capacity), self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def reset(self) -> None:
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_refill = _time.time()


_endpoint_buckets: Dict[str, TokenBucket] = {}
_endpoint_buckets_lock = threading.Lock()


def get_endpoint_bucket(name: str, capacity: int = 5, refill_rate: float = 0.5) -> TokenBucket:
    """Return (creating if needed) the TokenBucket for a named endpoint."""
    with _endpoint_buckets_lock:
        bucket = _endpoint_buckets.get(name)
        if bucket is None:
            bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate)
            _endpoint_buckets[name] = bucket
        return bucket


def consume_endpoint_token(name: str) -> bool:
    return get_endpoint_bucket(name).consume(1.0)


# ============ Rules Engine Singleton ============

_rules_engine = None
_rules_engine_lock = threading.Lock()


def _get_rules_engine():
    global _rules_engine
    if _rules_engine is None:
        with _rules_engine_lock:
            if _rules_engine is None:
                from augur.rules import RulesEngine
                _rules_engine = RulesEngine()
    return _rules_engine


# ============ I18n helpers ============

_i18n_cache: Dict[str, Dict[str, Any]] = {}


def _load_translations(lang: str = "zh") -> Dict[str, Any]:
    if lang in _i18n_cache:
        return _i18n_cache[lang]
    i18n_dir = Path(__file__).parent / "i18n"
    filepath = i18n_dir / f"{lang}.json"
    if filepath.exists():
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            _i18n_cache[lang] = data
            return data
        except Exception:
            pass
    return {}


def _i18n_context(lang: str = "zh", request: Any = None) -> Dict[str, Any]:
    if request is not None and lang == "zh":
        cookie_lang = request.cookies.get("augur_lang")
        if cookie_lang in ("en", "zh"):
            lang = cookie_lang
    return {"t": _load_translations(lang), "lang": lang}


# ============ History helper ============

def _save_history_safe(ticker: str, result: Any) -> None:
    try:
        from augur.history import save_analysis
        save_analysis(ticker, result)
    except Exception:
        pass
