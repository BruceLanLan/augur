
"""Research pack digest — verify exported evidence packs (G05 enhancement)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional


def compute_manifest_digest(pack_dir: Path) -> Dict[str, str]:
    """Compute SHA-256 digests for all files in an evidence pack.

    Returns dict mapping relative file path → hex digest.
    """
    if not pack_dir.exists():
        return {}
    digests: Dict[str, str] = {}
    for f in sorted(pack_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(pack_dir).as_posix()
            digests[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    return digests


def verify_pack_integrity(pack_dir: Path, manifest: dict) -> Dict[str, bool]:
    """Verify each manifest entry matches the file on disk.

    Returns dict mapping path → matched (bool).
    """
    if "files" not in manifest:
        return {}
    results: Dict[str, bool] = {}
    for rel, expected_digest in manifest["files"].items():
        f = pack_dir / rel
        if not f.exists():
            results[rel] = False
            continue
        actual = hashlib.sha256(f.read_bytes()).hexdigest()
        results[rel] = actual == expected_digest
    return results
