# -*- coding: utf-8 -*-
"""
augur.datasources.cn_fund_nav_provider - A-share ETF NAV from Sina (v14)

yfinance has no NAV for Shanghai / Shenzhen ETFs. Sina's free quote endpoint
does, without a key, as long as a ``Referer`` header is sent::

    GET https://hq.sinajs.cn/list=f_510300,sh510300
    var hq_str_f_510300="华泰柏瑞沪深300ETF,3.9718,1.7998,4.0383,2026-11-25,241.196";
    var hq_str_sh510300="沪深300ETF华泰柏瑞,3.987,3.970,3.974,...,2026-11-26,15:00:00,00,";

``f_<code>`` fields: name, unit NAV, accumulated NAV, previous NAV, NAV date,
fund size. The exchange quote (``sh``/``sz``) gives open, previous close,
price, ... and the quote date at index 30; it supplies the close on the NAV
date when the yfinance history is missing that bar.

Not an official API: every failure (network, HTTP status, format change)
returns ``{}`` and the ETF profile simply has no NAV.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from augur.datasources.base import safe_num
from augur.datasources.fund_profile import cn_etf_code

logger = logging.getLogger(__name__)

SINA_URL = "https://hq.sinajs.cn/list={symbols}"
SINA_HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0",
}
TIMEOUT_SECONDS = 5.0

_LINE_RE = re.compile(r'var hq_str_(\w+)="([^"]*)";?')
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _exchange_prefix(ticker: str) -> str:
    return "sh" if ticker.strip().upper().endswith(".SS") else "sz"


def parse_sina_response(text: str, code: str, exchange: str) -> Dict[str, Any]:
    """Parse a Sina ``hq_str`` response into NAV + quote fields.

    Returns ``{}`` when the NAV line is missing, empty or malformed.
    Keys: ``name, nav, nav_date`` and, when the exchange quote parses,
    ``price, prev_close, quote_date``.
    """
    lines = {m.group(1): m.group(2) for m in _LINE_RE.finditer(text or "")}
    raw = lines.get(f"f_{code}", "")
    parts = raw.split(",") if raw else []
    if len(parts) < 5:
        return {}
    nav, nav_date = safe_num(parts[1]), parts[4].strip()
    if nav <= 0 or not _DATE_RE.match(nav_date):
        return {}
    out: Dict[str, Any] = {"name": parts[0].strip(), "nav": nav, "nav_date": nav_date}

    quote = (lines.get(f"{exchange}{code}", "") or "").split(",")
    if len(quote) > 30 and _DATE_RE.match(quote[30].strip()):
        prev_close, price = safe_num(quote[2]), safe_num(quote[3])
        if prev_close > 0:
            out["prev_close"] = prev_close
        if price > 0:
            out["price"] = price
        out["quote_date"] = quote[30].strip()
    return out


def _http_get(url: str) -> str:
    import httpx

    resp = httpx.get(url, headers=SINA_HEADERS, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.content.decode("gbk", errors="replace")


def fetch_cn_fund_nav(ticker: str) -> Dict[str, Any]:
    """Latest NAV for an A-share ETF ticker (``510300.SS``); ``{}`` on any failure."""
    code = cn_etf_code(ticker)
    if not code:
        return {}
    exchange = _exchange_prefix(ticker)
    try:
        text = _http_get(SINA_URL.format(symbols=f"f_{code},{exchange}{code}"))
    except Exception as exc:
        logger.info("Sina NAV lookup failed for %s: %s", ticker, exc)
        return {}
    try:
        return parse_sina_response(text, code, exchange)
    except Exception as exc:  # pragma: no cover - parser is defensive already
        logger.info("Sina NAV parse failed for %s: %s", ticker, exc)
        return {}


def close_on_nav_date(nav_info: Dict[str, Any]) -> float:
    """Close of the NAV's date taken from the Sina quote, or 0 when unknown.

    Sina publishes the NAV of day T on the evening of T, so the quote is
    either still dated T (use the last price) or dated the next session
    (use its previous close). Any other combination returns 0.
    """
    nav_date, quote_date = nav_info.get("nav_date", ""), nav_info.get("quote_date", "")
    if not nav_date or not quote_date:
        return 0.0
    if quote_date == nav_date:
        return float(nav_info.get("price", 0.0) or 0.0)
    if quote_date > nav_date:
        return float(nav_info.get("prev_close", 0.0) or 0.0)
    return 0.0
