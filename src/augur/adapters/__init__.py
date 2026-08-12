# -*- coding: utf-8 -*-
"""
augur.adapters — Schema-only adapters for optional third-party data providers.

Each adapter defines a mapping from the provider's output shape into
augur's canonical EvidenceItem schema without importing the provider at
module level.  ImportError guards ensure graceful degradation when the
provider is not installed.
"""

from augur.adapters.openbb_adapter import (
    OpenBBMetamodel,
    is_openbb_available,
    to_evidence_item,
)

__all__ = [
    "OpenBBMetamodel",
    "is_openbb_available",
    "to_evidence_item",
]
