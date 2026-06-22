# -*- coding: utf-8 -*-
"""Optional meta-model for consensus score blending."""

from typing import Dict, Optional


class MetaModel:
    """Lightweight stub — blends toward median agent score when loaded."""

    def __init__(self):
        self._active = True

    @classmethod
    def load(cls) -> Optional["MetaModel"]:
        return cls()

    def predict(self, agent_scores: Dict[str, float]) -> float:
        if not agent_scores:
            return 5.0
        scores = sorted(agent_scores.values())
        mid = len(scores) // 2
        if len(scores) % 2:
            return scores[mid]
        return (scores[mid - 1] + scores[mid]) / 2.0
