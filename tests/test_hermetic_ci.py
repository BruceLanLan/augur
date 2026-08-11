# -*- coding: utf-8 -*-
"""CI guardrails: assert augur is imported from this checkout, not a
system-wide editable install, and __version__ matches pyproject.toml."""

import os
import re
from pathlib import Path


def test_augur_import_path_is_this_checkout():
    """augur.__file__ must point into this working tree.

    If this fails, a stale editable install (``pip install -e .`` in a
    different directory) is shadowing the local source.
    """
    import augur

    augur_file = Path(augur.__file__).resolve()
    cwd = Path.cwd().resolve()

    # Accept either src/augur/__init__.py (editable install) or the bare
    # augur/__init__.py (PYTHONPATH).  Reject anything outside cwd.
    try:
        augur_file.relative_to(cwd)
    except ValueError:
        raise AssertionError(
            f"augur.__file__ = {augur_file} is outside the current "
            f"working directory ({cwd}). A system or editable install "
            f"from another location is likely shadowing this checkout. "
            f"Uninstall it (pip uninstall augur-agents) and re-run "
            f"with PYTHONPATH=src."
        )


def test_augur_version_matches_pyproject():
    """augur.__version__ must equal the version declared in pyproject.toml."""
    import augur

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")

    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m is not None, "Could not find version in pyproject.toml"
    toml_version = m.group(1)

    assert augur.__version__ == toml_version, (
        f"augur.__version__ = {augur.__version__!r} but "
        f"pyproject.toml declares {toml_version!r}"
    )
