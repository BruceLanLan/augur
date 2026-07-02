# -*- coding: utf-8 -*-
"""Portfolio risk decomposition API.

Decomposes an existing (client-supplied) holdings list into:
  - per-holding variance contribution (Euler decomposition of portfolio
    variance via the historical-returns covariance matrix)
  - portfolio beta (weight-averaged MarketContext.beta_1y)
  - sector concentration
  - diversification (Herfindahl-Hirschman Index, both weight-based and
    risk-contribution-based — these can diverge a lot when holdings are
    correlated, which is the whole point of showing both)

Reuses the covariance/returns plumbing already built for the Markowitz
optimizer (``augur.optimizer.PortfolioOptimizer``) rather than duplicating it.
"""

import hashlib
import random
import re
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_TRADING_DAYS = 252


class PortfolioHolding(BaseModel):
    ticker: str
    qty: float
    current_price: float = 0.0


class PortfolioRiskBody(BaseModel):
    holdings: List[PortfolioHolding]


@router.post("/api/portfolio/risk", summary="投资组合风险分解")
async def api_portfolio_risk(body: PortfolioRiskBody):
    if not body.holdings:
        raise HTTPException(status_code=400, detail="Portfolio has no holdings")
    if len(body.holdings) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 holdings per portfolio")

    # Aggregate multiple lots of the same ticker into one position.
    agg: Dict[str, Dict[str, float]] = {}
    for h in body.holdings:
        ticker = h.ticker.strip().upper()
        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {h.ticker}")
        if h.qty <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid quantity for {ticker}")
        entry = agg.setdefault(ticker, {"qty": 0.0, "price": h.current_price})
        entry["qty"] += h.qty
        if h.current_price > 0:
            entry["price"] = h.current_price

    tickers = list(agg.keys())
    values = {t: agg[t]["qty"] * agg[t]["price"] for t in tickers}
    total_value = sum(values.values())
    if total_value <= 0:
        raise HTTPException(
            status_code=400,
            detail="Portfolio has zero market value (missing current prices)",
        )

    weights = {t: values[t] / total_value for t in tickers}
    weight_vec = [weights[t] for t in tickers]

    # --- Historical returns for covariance (reuse PortfolioOptimizer plumbing) ---
    from augur.optimizer import PortfolioOptimizer, matrix_vector_multiply, vector_dot

    optimizer = PortfolioOptimizer()
    returns_data: Dict[str, List[float]] = {}
    data_source = "mock"
    try:
        from augur.data import fetch_history
        real_count = 0
        for t in tickers:
            hist = fetch_history(t, period="3mo")
            if hist and len(hist) >= 10:
                closes = [d["close"] for d in hist if d.get("close") and d["close"] > 0]
                if len(closes) >= 10:
                    returns_data[t] = [
                        (closes[i] - closes[i - 1]) / closes[i - 1]
                        for i in range(1, len(closes))
                    ]
                    real_count += 1
        if real_count == len(tickers):
            data_source = "live"
        elif real_count > 0:
            data_source = "partial"
    except Exception:
        pass

    for t in tickers:
        if t not in returns_data:
            seed = int(hashlib.sha256(t.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            returns_data[t] = [rng.gauss(0.001, 0.02) for _ in range(60)]

    if len(tickers) == 1:
        rets = returns_data[tickers[0]]
        mean_r = sum(rets) / len(rets) if rets else 0.0
        port_var = (
            sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
        )
        risk_contrib_pct = {tickers[0]: 100.0}
    else:
        returns_list = [returns_data[t] for t in tickers]
        cov = optimizer.covariance_matrix(returns_list)
        cov_w = matrix_vector_multiply(cov, weight_vec)
        port_var = vector_dot(weight_vec, cov_w)

        risk_contrib_pct = {}
        if port_var > 1e-12:
            for i, t in enumerate(tickers):
                contrib = weight_vec[i] * cov_w[i]
                risk_contrib_pct[t] = round(contrib / port_var * 100, 2)
        else:
            # No measurable variance (e.g. all-flat mock data) — fall back to weight.
            for t in tickers:
                risk_contrib_pct[t] = round(weights[t] * 100, 2)

    port_vol_annual = (max(port_var, 0.0) ** 0.5) * (_TRADING_DAYS ** 0.5)

    # --- Beta and sector (live MarketContext lookup, never raises) ---
    beta_by_ticker: Dict[str, float] = {}
    sector_by_ticker: Dict[str, str] = {}
    try:
        from augur.data import fetch_market_context
        for t in tickers:
            try:
                ctx = fetch_market_context(t)
                beta_by_ticker[t] = ctx.beta_1y if ctx.beta_1y else 1.0
                sector_by_ticker[t] = ctx.sector or "Unknown"
            except Exception:
                beta_by_ticker[t] = 1.0
                sector_by_ticker[t] = "Unknown"
    except Exception:
        for t in tickers:
            beta_by_ticker[t] = 1.0
            sector_by_ticker[t] = "Unknown"

    portfolio_beta = sum(weights[t] * beta_by_ticker[t] for t in tickers)

    # --- Sector concentration ---
    sector_weights: Dict[str, float] = {}
    for t in tickers:
        sec = sector_by_ticker[t]
        sector_weights[sec] = sector_weights.get(sec, 0.0) + weights[t]
    sector_concentration = [
        {"sector": s, "weight_pct": round(w * 100, 2)}
        for s, w in sorted(sector_weights.items(), key=lambda kv: -kv[1])
    ]

    # --- Diversification (Herfindahl-Hirschman Index) ---
    # hhi_weight/effective_n_weight: standard position-size concentration.
    # hhi_risk/effective_n_risk: concentration of actual variance contribution —
    # can be much worse than the weight-based number when holdings are correlated.
    hhi_weight = sum(w * w for w in weight_vec)
    effective_n_weight = round(1.0 / hhi_weight, 2) if hhi_weight > 0 else 0.0
    hhi_risk = sum((risk_contrib_pct[t] / 100.0) ** 2 for t in tickers)
    effective_n_risk = round(1.0 / hhi_risk, 2) if hhi_risk > 0 else 0.0

    holdings_resp = [
        {
            "ticker": t,
            "weight_pct": round(weights[t] * 100, 2),
            "value": round(values[t], 2),
            "beta": round(beta_by_ticker[t], 3),
            "sector": sector_by_ticker[t],
            "risk_contribution_pct": risk_contrib_pct[t],
        }
        for t in tickers
    ]
    holdings_resp.sort(key=lambda h: -h["weight_pct"])

    return {
        "status": "ok",
        "total_value": round(total_value, 2),
        "data_source": data_source,
        "portfolio": {
            "volatility_annual_pct": round(port_vol_annual * 100, 2),
            "beta": round(portfolio_beta, 3),
            "diversification": {
                "hhi_weight": round(hhi_weight, 4),
                "effective_n_weight": effective_n_weight,
                "hhi_risk": round(hhi_risk, 4),
                "effective_n_risk": effective_n_risk,
            },
        },
        "holdings": holdings_resp,
        "sector_concentration": sector_concentration,
    }
