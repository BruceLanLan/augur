# -*- coding: utf-8 -*-
"""
augur.history - Analysis history storage

Saves analysis results to ~/.augur/history/ as JSON files.
Each file is named {timestamp}_{ticker}.json.

Functions:
    save_analysis(ticker, result_dict) - Save an analysis result
    list_history(limit=50) - List recent history records
    get_history(history_id) - Get a specific record by ID
    clear_history() - Delete all history records
    delete_history(history_id) - Delete a specific record
"""

import json
import os
import threading
import time as _time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

HISTORY_DIR = Path.home() / ".augur" / "history"

# Lock protecting file writes so concurrent requests don't corrupt history files
_write_lock = threading.Lock()

# Simple cache for count_history() to avoid re-globbing on every call
_count_cache_value: int = 0
_count_cache_time: float = 0.0
_COUNT_CACHE_TTL: float = 5.0  # seconds


def _invalidate_count_cache() -> None:
    """Force count_history() to refresh on next call."""
    global _count_cache_time
    _count_cache_time = 0.0


def _ensure_dir():
    """Ensure history directory exists."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _safe_ticker_label(ticker: str) -> str:
    """Return a filesystem-safe ticker label for history filenames."""
    label = (ticker or "").strip().upper()
    if not label or any(c in label for c in ('/', '\\', '..', '\0')):
        return "INVALID"
    if len(label) > 15:
        label = label[:15]
    return label


def save_analysis(ticker: str, result_dict: Dict[str, Any]) -> str:
    """Save an analysis result to history.

    Args:
        ticker: Stock ticker symbol.
        result_dict: Full analysis result dictionary.

    Returns:
        The history_id (filename without extension).
    """
    _ensure_dir()
    safe_ticker = _safe_ticker_label(ticker)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    history_id = f"{timestamp}_{safe_ticker}"
    filepath = HISTORY_DIR / f"{history_id}.json"

    record = {
        "id": history_id,
        "ticker": safe_ticker,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "result": result_dict,
    }

    # Atomic write: serialize to a temp file then rename to prevent concurrent
    # readers from seeing a half-written file.
    tmp_path = filepath.with_suffix(".json.tmp")
    with _write_lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)

    _invalidate_count_cache()
    return history_id


def list_history(limit: int = 50, page: Optional[int] = None, per_page: int = 20) -> List[Dict[str, Any]]:
    """List recent analysis history records.

    Args:
        limit: Maximum number of records to return (used when page is None).
        page: Page number (1-indexed). If provided, pagination is used.
        per_page: Number of records per page (default 20).

    Returns:
        List of summary dicts with id, ticker, signal, score, timestamp.
    """
    _ensure_dir()
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)

    if page is not None:
        # Pagination mode: slice based on page and per_page
        start = (page - 1) * per_page
        end = start + per_page
        target_files = files[start:end]
    else:
        target_files = files[:limit]

    records = []
    for f in target_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            consensus = data.get("result", {}).get("consensus", {})
            records.append({
                "id": data.get("id", f.stem),
                "ticker": data.get("ticker", ""),
                "signal": consensus.get("signal", "unknown"),
                "score": consensus.get("score", 0),
                "timestamp": data.get("timestamp", ""),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return records


def count_history() -> int:
    """Count total number of history records.

    Uses a module-level cache with a 5-second TTL to avoid
    re-globbing the directory on every paginated request.

    Returns:
        Total number of history JSON files.
    """
    global _count_cache_value, _count_cache_time
    now = _time.time()
    if (now - _count_cache_time) < _COUNT_CACHE_TTL:
        return _count_cache_value
    _ensure_dir()
    _count_cache_value = len(list(HISTORY_DIR.glob("*.json")))
    _count_cache_time = now
    return _count_cache_value


def get_history(history_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific history record by ID.

    Args:
        history_id: The record ID (filename without .json).

    Returns:
        Full record dict, or None if not found.
    """
    # Path traversal protection: basic char check + resolved path validation
    if not history_id or any(c in history_id for c in ('/', '\\', '..', '\0')):
        return None

    _ensure_dir()
    filepath = (HISTORY_DIR / f"{history_id}.json").resolve()
    if not str(filepath).startswith(str(HISTORY_DIR.resolve())):
        return None

    if not filepath.exists():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def clear_history() -> int:
    """Delete all history records.

    Returns:
        Number of records deleted.
    """
    _ensure_dir()
    files = list(HISTORY_DIR.glob("*.json"))
    count = 0
    for f in files:
        try:
            f.unlink()
            count += 1
        except OSError:
            continue
    _invalidate_count_cache()
    return count


def delete_history(history_id: str) -> bool:
    """Delete a specific history record.

    Args:
        history_id: The record ID (filename without .json).

    Returns:
        True if deleted, False if not found.
    """
    # Path traversal protection: basic char check + resolved path validation
    if not history_id or any(c in history_id for c in ('/', '\\', '..', '\0')):
        return False

    _ensure_dir()
    filepath = (HISTORY_DIR / f"{history_id}.json").resolve()
    if not str(filepath).startswith(str(HISTORY_DIR.resolve())):
        return False

    if not filepath.exists():
        return False

    try:
        filepath.unlink()
        _invalidate_count_cache()
        return True
    except OSError:
        return False
