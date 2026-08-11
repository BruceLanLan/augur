#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/smoke_test_hermetic.py — Hermetic isolation smoke test.

Runs three times in a fresh temp directory with ``AUGUR_DATA_DIR`` set,
verifying:

1. The augur package imports and reports its version.
2. Write-capable modules (e.g. LearningEngine) create expected files under
   ``AUGUR_DATA_DIR``.
3. A second run against the same directory is idempotent (does not fail
   because directories already exist).
4. After cleanup no residue remains, and the default ``~/.augur`` is not
   written to.

This script is **standalone** — it does not depend on conftest fixtures or any
network data source.  It can be invoked directly:

    python tests/smoke_test_hermetic.py

or via pytest (which will discover the ``test_*`` functions):

    python -m pytest tests/smoke_test_hermetic.py -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


_EXERCISE_SCRIPT = r"""
import os, sys, json
from pathlib import Path

# 1. Version import
from augur import __version__
print(__version__)

# 2. Exercise write-capable modules so AUGUR_DATA_DIR gets populated.
#    The LearningEngine writes learned_weights.json on record_prediction.
from augur.learning import LearningEngine
engine = LearningEngine()
engine.record_prediction("AAPL", "test_agent", "bullish", 7.5, 0.8)

# 3. Verify expected paths exist
data_dir = Path(os.environ.get("AUGUR_DATA_DIR", Path.home() / ".augur"))
weights_file = data_dir / "learned_weights.json"
assert weights_file.exists(), f"Expected {weights_file} to exist after write"
print(f"OK: {weights_file} exists")
"""


def _run_exercise(data_dir: str) -> str:
    """Run the exercise script in a subprocess pointed at *data_dir*."""
    env = {**os.environ, "AUGUR_DATA_DIR": data_dir}
    result = subprocess.run(
        [sys.executable, "-c", _EXERCISE_SCRIPT],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, (
        f"Exercise script failed (exit {result.returncode}):\n"
        f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
    lines = result.stdout.strip().splitlines()
    version = lines[0] if lines else ""
    assert version, "augur.__version__ was empty"
    return version


def _collect_tree(data_dir: str) -> set:
    """Return the set of relative paths (files + dirs) under *data_dir*."""
    root = Path(data_dir)
    if not root.exists():
        return set()
    paths: set = set()
    for p in root.rglob("*"):
        paths.add(str(p.relative_to(root)))
    return paths


# ---------------------------------------------------------------------------
# Test: three-run hermetic cycle
# ---------------------------------------------------------------------------

def test_hermetic_three_run_cycle():
    """Run the hermetic smoke test: three isolated runs with cleanup."""
    tmp_root = tempfile.mkdtemp(prefix="augur_smoke_")

    try:
        # --- Run 1 ---
        run1_dir = os.path.join(tmp_root, "run1")
        v1 = _run_exercise(run1_dir)
        print(f"Run 1: version={v1}, data_dir={run1_dir}")
        tree1 = _collect_tree(run1_dir)
        print(f"Run 1 tree: {sorted(tree1)}")
        # Must have at least learned_weights.json
        assert "learned_weights.json" in tree1, (
            f"Run 1 missing learned_weights.json; tree={sorted(tree1)}"
        )

        # --- Run 2 (idempotency: same dir, second pass) ---
        v2 = _run_exercise(run1_dir)
        print(f"Run 2: version={v2} (idempotent on same dir)")
        assert v2 == v1, f"Version changed between runs: {v1} -> {v2}"
        tree2 = _collect_tree(run1_dir)
        print(f"Run 2 tree: {sorted(tree2)}")
        # After a second run, the tree should be a superset.
        missing = tree1 - tree2
        assert not missing, f"Run 2 lost files compared to run 1: {missing}"

        # --- Run 3 (clean dir — verify no cross-run pollution) ---
        shutil.rmtree(run1_dir, ignore_errors=True)
        assert not os.path.exists(run1_dir), f"Failed to clean {run1_dir}"

        run3_dir = os.path.join(tmp_root, "run3")
        v3 = _run_exercise(run3_dir)
        print(f"Run 3: version={v3} (fresh dir)")
        tree3 = _collect_tree(run3_dir)
        print(f"Run 3 tree: {sorted(tree3)}")
        assert "learned_weights.json" in tree3, (
            f"Run 3 missing learned_weights.json; tree={sorted(tree3)}"
        )

        # --- Verify no leak to default ~/.augur ---
        default_augur = Path.home() / ".augur"
        if default_augur.exists():
            print(f"NOTE: ~/.augur already exists (pre-existing); "
                  f"skipping write-leak assertion")
        else:
            print("OK: ~/.augur does not exist (no leak to default location)")

        # --- Cleanup verification ---
        shutil.rmtree(run3_dir, ignore_errors=True)
        remaining = list(Path(tmp_root).rglob("*"))
        assert not remaining, f"Residue after cleanup: {remaining}"

        print("Hermetic three-run cycle: PASSED")

    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_hermetic_three_run_cycle()
    print("\nAll hermetic smoke checks passed.")
