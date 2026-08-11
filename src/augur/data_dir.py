# -*- coding: utf-8 -*-
"""
augur.data_dir — Unified data-directory resolution.

All persistent paths in augur MUST derive from ``get_data_dir()``.
Set the ``AUGUR_DATA_DIR`` environment variable to override the default
(``~/.augur``); when unset behaviour is unchanged from prior releases.
"""

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Return the augur data root directory.

    Reads ``AUGUR_DATA_DIR`` from the environment; defaults to
    ``~/.augur`` when the variable is absent or empty.
    """
    env = os.environ.get("AUGUR_DATA_DIR", "")
    if env:
        return Path(env)
    return Path.home() / ".augur"
