# -*- coding: utf-8 -*-
"""Portfolio risk analysis — concentration + correlation basics (portfolio enhancement)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PositionRisk:
    ticker: str
    weight: float            # portfolio weight 0-1
    volatility_annualized: float = 0.0
    beta: float = 1.0
    contribution_to_risk: float = 0.0  # weight × volatility


@dataclass
class PortfolioRiskReport:
    positions: List[PositionRisk] = field(default_factory=list)
    total_volatility: float = 0.0
    concentration_hhi: float = 0.0       # Herfindahl index
    max_position_weight: float = 0.0
    diversification_score: float = 0.0   # 1/HHI normalized
    risk_summary: str = ""


class PortfolioRiskAnalyzer:
    """Compute portfolio concentration and risk contribution metrics."""

    def analyze(self, holdings: Dict[str, float]) -> PortfolioRiskReport:
        """Analyze a portfolio dict of {ticker: weight}.

        Args:
            holdings: Dict mapping ticker → portfolio weight (0-1).

        Returns:
            PortfolioRiskReport with concentration and risk metrics.
        """
        total = sum(holdings.values())
        if total <= 0:
            return PortfolioRiskReport(risk_summary="empty portfolio")

        positions: List[PositionRisk] = []
        hhi = 0.0
        max_w = 0.0
        for ticker, weight in sorted(holdings.items(), key=lambda x: -x[1]):
            w = weight / total
            positions.append(PositionRisk(ticker=ticker, weight=round(w, 4)))
            hhi += w * w
            max_w = max(max_w, w)

        # Diversification: 1/HHI normalized to [0,1] where 1 = perfectly diversified
        n = len(positions)
        diversification = (1.0 / max(hhi, 1e-9) / n) if n > 0 else 0.0
        diversification = min(1.0, diversification)

        # Risk summary
        if max_w > 0.4:
            summary = "concentrated — largest position exceeds 40%"
        elif max_w > 0.25:
            summary = "moderately concentrated"
        elif n >= 8 and diversification > 0.4:
            summary = "well diversified"
        else:
            summary = "adequate diversification"

        return PortfolioRiskReport(
            positions=positions,
            total_volatility=0.0,  # requires price history — left for extension
            concentration_hhi=round(hhi, 4),
            max_position_weight=round(max_w, 4),
            diversification_score=round(diversification, 4),
            risk_summary=summary,
        )
