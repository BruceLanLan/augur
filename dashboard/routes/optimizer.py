"""Portfolio Optimizer routes and I18n API."""

import hashlib
import json
import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from dashboard.deps import _i18n_context, consume_endpoint_token, templates

router = APIRouter()

_I18N_DIR = Path(__file__).parent.parent / "i18n"


# ============ Portfolio Optimizer ============

class OptimizeBody(BaseModel):
    tickers: List[str]
    risk_free_rate: float = 0.02


@router.get("/optimizer", response_class=HTMLResponse)
async def optimizer_page(request: Request):
    ctx = {"title": "Portfolio Optimizer"}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="optimizer.html", context=ctx)


@router.post("/api/optimize")
async def api_optimize(body: OptimizeBody):
    if not consume_endpoint_token("api_optimize"):
        raise HTTPException(
            status_code=429,
            detail="Optimize rate limit exceeded. Please wait and retry.",
        )
    from augur.optimizer import PortfolioOptimizer
    import random
    if not body.tickers or len(body.tickers) > 10:
        raise HTTPException(status_code=400, detail="需要1-10个股票代码")
    for t in body.tickers:
        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', t):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {t}")

    returns_data = {}
    data_source = "mock"

    try:
        from augur.data import fetch_history
        real_count = 0
        for ticker in body.tickers:
            hist = fetch_history(ticker.upper(), period="3mo")
            if hist and len(hist) >= 10:
                closes = [h["close"] for h in hist if h.get("close") and h["close"] > 0]
                if len(closes) >= 10:
                    daily_returns = [
                        (closes[i] - closes[i - 1]) / closes[i - 1]
                        for i in range(1, len(closes))
                    ]
                    returns_data[ticker.upper()] = daily_returns
                    real_count += 1
        if real_count == len(body.tickers):
            data_source = "live"
        elif real_count > 0:
            data_source = "partial"
    except Exception:
        pass

    for ticker in body.tickers:
        if ticker.upper() not in returns_data:
            seed = int(hashlib.sha256(ticker.upper().encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            returns_data[ticker.upper()] = [rng.gauss(0.001, 0.02) for _ in range(60)]

    optimizer = PortfolioOptimizer()
    result = optimizer.optimize(returns_data, risk_free_rate=body.risk_free_rate)

    _TRADING_DAYS = 252
    frontier_raw = optimizer.efficient_frontier(
        returns_data, risk_free_rate=body.risk_free_rate, n_points=40
    )
    frontier_points = [
        {
            "risk": round(fp.volatility * (_TRADING_DAYS ** 0.5) * 100, 4),
            "return": round(fp.expected_return * _TRADING_DAYS * 100, 4),
        }
        for fp in frontier_raw
    ]

    opt_dict = result.to_dict()
    opt_dict["expected_return_annual"] = round(opt_dict["expected_return"] * _TRADING_DAYS, 6)
    opt_dict["volatility_annual"] = round(opt_dict["volatility"] * (_TRADING_DAYS ** 0.5), 6)
    opt_dict["sharpe_ratio_annual"] = round(opt_dict["sharpe_ratio"] * (_TRADING_DAYS ** 0.5), 4)

    tickers_list = list(returns_data.keys())
    asset_points = []
    for ticker in tickers_list:
        rets = returns_data[ticker]
        if len(rets) < 2:
            continue
        mean_r = sum(rets) / len(rets)
        var_r = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
        vol_r = var_r ** 0.5
        asset_points.append({
            "ticker": ticker,
            "risk": round(vol_r * (_TRADING_DAYS ** 0.5) * 100, 4),
            "return": round(mean_r * _TRADING_DAYS * 100, 4),
        })

    return {
        "status": "ok",
        "portfolio": opt_dict,
        "tickers": [t.upper() for t in body.tickers],
        "data_source": data_source,
        "frontier_points": frontier_points,
        "asset_points": asset_points,
    }


# ============ I18n API ============

@router.get("/api/i18n/{lang}")
async def api_i18n(lang: str):
    if lang not in ("en", "zh"):
        raise HTTPException(status_code=400, detail="Supported languages: en, zh")
    filepath = _I18N_DIR / f"{lang}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Language file not found: {lang}")
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"翻译文件格式错误: {e}")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=500, detail=f"翻译文件编码错误: {e}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"翻译文件读取失败: {e}")
    return data


@router.post("/api/lang/{lang}")
async def api_set_lang(lang: str):
    if lang not in ("en", "zh"):
        raise HTTPException(status_code=400, detail="Supported languages: en, zh")
    response = JSONResponse(content={"status": "ok", "lang": lang})
    response.set_cookie(key="augur_lang", value=lang, max_age=365 * 24 * 3600, httponly=False, samesite="lax")
    return response
