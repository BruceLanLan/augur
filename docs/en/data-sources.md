English | [中文](data-sources.md)

# Data Source API Integration Guide

This document describes how to integrate real-time data APIs for investment analysis Skills, covering stock quotes, financial data, options data, 13F holdings, and more.

> **Note**: Sections 1-6 are early-stage design examples (standalone code that does not necessarily match `src/augur/`). **The actual provider chain, environment variables, caches and EDGAR behavior are in Sections 7-9.**

---

## 1. Recommended API Options

### 1. Yahoo Finance API (Free, Recommended)

**Advantages**: Free, comprehensive data, global market coverage, no application required

**Integration**: Use the `yfinance` Python library

```python
import yfinance as yf

# Get stock data
ticker = yf.Ticker("00700.HK")

# Real-time/historical prices
hist = ticker.history(period="1d")  # Today's price
hist = ticker.history(period="1y")  # 1 year history

# Financial statements
income_stmt = ticker.financials        # Income statement
balance_sheet = ticker.balance_sheet    # Balance sheet
cash_flow = ticker.cashflow             # Cash flow statement

# Recommendations
recommendations = ticker.recommendations  # Analyst ratings
analyst_price_targets = ticker.analyst_price_targets  # Price targets

# Options data
options = ticker.options                  # Expiration dates
calls = ticker.option_chain(date)[0]     # Call option chain
puts = ticker.option_chain(date)[1]      # Put option chain

# Key statistics
info = ticker.info  # PE, EPS, dividends, 50-day MA, and all other info
```

### 2. Alpha Vantage (Free/Paid)

**Advantages**: Professional financial data, GAAP/IFRS statements, real-time prices

**Sign up**: https://www.alphavantage.co/ (Free API Key)

```python
import requests

API_KEY = "YOUR_FREE_KEY"
BASE_URL = "https://www.alphavantage.co/query"

# Stock quote
def get_quote(symbol):
    url = f"{BASE_URL}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
    return requests.get(url).json()

# Financial statements
def get_income_statement(symbol):
    url = f"{BASE_URL}?function=INCOME_STATEMENT&symbol={symbol}&apikey={API_KEY}"
    return requests.get(url).json()

# Key technical indicators
def get_overview(symbol):
    url = f"{BASE_URL}?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}"
    return requests.get(url).json()
```

### 3. SEC EDGAR API (Free, 13F Holdings)

**Use case**: 13F institutional holdings, 8-K material events, 10-K/10-Q annual and quarterly reports

```python
import requests

# Get XBRL company facts (companyfacts; NOTE: this is not 13F holdings -- 13F requires parsing type=13F filings)
def get_13f_filings(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": "Your Name your@email.com"}
    return requests.get(url, headers=headers).json()

# Get latest 13F
def get_latest_13f(cik):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F&owner=include&count=1"
    return requests.get(url, headers={"User-Agent": "Your Name your@email.com"}).text

# Search company CIK
def search_company(company_name):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=companysearch&company={company_name}"
    return requests.get(url, headers={"User-Agent": "Your Name your@email.com"}).text
```

### 4. Finnhub (Free/Paid)

**Advantages**: Real-time technical indicators, candlestick charts, news sentiment

**Sign up**: https://finnhub.io/ (Free tier available)

```python
import requests

API_KEY = "YOUR_KEY"
BASE_URL = "https://finnhub.io/api/v1"

# Candlestick data
def get_candles(symbol, resolution="D", from_time=None, to_time=None):
    url = f"{BASE_URL}/stock/candle?symbol={symbol}&resolution={resolution}&from={from_time}&to={to_time}&token={API_KEY}"
    return requests.get(url).json()

# Technical indicators
def get_technical_indicators(symbol, indicator="sma", params={}):
    url = f"{BASE_URL}/scan/technical-indicator?symbol={symbol}&indicator={indicator}&token={API_KEY}"
    return requests.get(url).json()

# Analyst ratings
def get_recommendations(symbol):
    url = f"{BASE_URL}/stock/recommendation?symbol={symbol}&token={API_KEY}"
    return requests.get(url).json()

# Earnings calendar
def get_earnings_calendar(from_date, to_date):
    url = f"{BASE_URL}/calendar/earnings?from={from_date}&to={to_date}&token={API_KEY}"
    return requests.get(url).json()
```

### 5. Crunchbase (VC/Primary Market)

**Use case**: Funding history, valuations, founder information, investors

```python
# Crunchbase API (paid, but has a free tier)
# https://data.crunchbase.com/docs

# Alternative: other public VC data APIs (not integrated in this project)
```

---

## 2. Integration into the Analysis Pipeline

### Data Retrieval Workflow

```
Analysis Request -> Auto-fetch Data -> Data Processing -> Analysis Output
                       |
    +------------------+------------------+------------------+
    |                  |                  |                  |
  Quote API      Financials API     13F API          Options API
    |                  |                  |                  |
  Real-time      Financial         Institutional    Volatility
  Prices         Data              Holdings
```

### Python Data Retrieval Script Example

```python
#!/usr/bin/env python3
"""
Investment Analysis Data Retrieval Script
Automatically fetches stock quotes, financial data, technical indicators, analyst ratings
"""

import yfinance as yf
import json
from datetime import datetime, timedelta

class StockDataFetcher:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.t = yf.Ticker(ticker)

    def get_price(self):
        """Get real-time price"""
        hist = self.t.history(period="1d")
        if not hist.empty:
            return {
                "current_price": hist['Close'].iloc[-1],
                "open": hist['Open'].iloc[0],
                "high": hist['High'].iloc[-1],
                "low": hist['Low'].iloc[-1],
                "volume": hist['Volume'].iloc[-1]
            }

    def get_technicals(self):
        """Get technical indicators"""
        info = self.t.info
        hist_50d = self.t.history(period="3mo")
        hist_200d = self.t.history(period="1y")

        return {
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "ma_50": hist_50d['Close'].mean() if len(hist_50d) >= 50 else None,
            "ma_200": hist_200d['Close'].mean() if len(hist_200d) >= 200 else None,
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
            "rsi_14": self._calculate_rsi(14),
        }

    def _calculate_rsi(self, period=14):
        """Calculate RSI"""
        hist = self.t.history(period="3mo")
        if len(hist) < period:
            return None
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def get_financials(self):
        """Get financial data"""
        try:
            income = self.t.financials
            balance = self.t.balance_sheet
            cashflow = self.t.cashflow
            return {
                "revenue": income.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income.index else None,
                "net_income": income.loc['Net Income'].iloc[0] if 'Net Income' in income.index else None,
                "gross_profit": income.loc['Gross Profit'].iloc[0] if 'Gross Profit' in income.index else None,
                "total_assets": balance.loc['Total Assets'].iloc[0] if 'Total Assets' in balance.index else None,
                "total_equity": balance.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in balance.index else None,
                "operating_cashflow": cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else None,
                "capital_expenditure": cashflow.loc['Capital Expenditures'].iloc[0] if 'Capital Expenditures' in cashflow.index else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_analyst_data(self):
        """Get analyst data"""
        info = self.t.info
        recommendations = self.t.recommendations
        return {
            "target_price": info.get("targetMeanPrice"),
            "target_low": info.get("targetLowPrice"),
            "target_high": info.get("targetHighPrice"),
            "recommendation": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "recent_recommendations": recommendations.to_dict() if recommendations is not None else None
        }

    def get_all_data(self):
        """Get all data"""
        return {
            "ticker": self.ticker,
            "timestamp": datetime.now().isoformat(),
            "price": self.get_price(),
            "technicals": self.get_technicals(),
            "financials": self.get_financials(),
            "analyst": self.get_analyst_data()
        }

# Usage example
if __name__ == "__main__":
    fetcher = StockDataFetcher("00700.HK")
    data = fetcher.get_all_data()
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
```

---

## 3. 13F Institutional Holdings Retrieval

```python
import requests
from bs4 import BeautifulSoup

def get_13f_holdings(company_name_or_cik):
    """
    Retrieve 13F institutional holdings data
    """
    # If input is a company name, search for CIK first
    if not company_name_or_cik.isdigit():
        search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={company_name_or_cik}&type=13F&count=1"
        headers = {"User-Agent": "Your Name your@email.com"}
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find CIK...
        cik = soup.find('a', {'id': 'documentsButton'})['href'].split('CIK=')[1].split('&')[0]
    else:
        cik = company_name_or_cik

    # Get latest 13F filing
    filings_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F&count=1"
    headers = {"User-Agent": "Your Name your@email.com", "Accept-Encoding": "gzip, deflate"}
    response = requests.get(filings_url, headers=headers)

    return response.text
```

---

## 4. Complete Investment Analysis Tool

```python
#!/usr/bin/env python3
"""
Complete Investment Analysis Data Tool
Supports: Quotes, Financials, Technical Indicators, Analyst Ratings, 13F Holdings, Options
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json

class InvestmentAnalysisTool:
    def __init__(self, ticker: str, market="US"):
        """
        Initialize
        market: US, HK, CN, JP, EU
        """
        self.ticker = ticker
        self.market = market
        self.t = yf.Ticker(ticker)

    # ========== Quote Data ==========
    def get_realtime_quote(self):
        """Real-time quote"""
        info = self.t.info
        hist = self.t.history(period="1d")
        hist_1y = self.t.history(period="1y")

        return {
            "symbol": self.ticker,
            "name": info.get("longName"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "change": info.get("regularMarketChange"),
            "change_pct": info.get("regularMarketChangePercent"),
            "open": info.get("regularMarketOpen"),
            "high": info.get("regularMarketDayHigh"),
            "low": info.get("regularMarketDayLow"),
            "volume": info.get("regularMarketVolume"),
            "avg_volume": info.get("averageVolume"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend": info.get("dividendRate"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "50d_ma": hist_1y['Close'].tail(50).mean() if len(hist_1y) >= 50 else None,
            "200d_ma": hist_1y['Close'].tail(200).mean() if len(hist_1y) >= 200 else None,
        }

    # ========== Financial Data ==========
    def get_financials(self):
        """Complete financial statements"""
        return {
            "income_statement": self._safe_get_data(self.t.financials),
            "balance_sheet": self._safe_get_data(self.t.balance_sheet),
            "cash_flow": self._safe_get_data(self.t.cashflow),
            "quarterly_financials": self._safe_get_data(self.t.quarterly_financials),
        }

    def _safe_get_data(self, df):
        """Safely get DataFrame"""
        if df is None or df.empty:
            return None
        return df.to_dict()

    # ========== Technical Indicators ==========
    def get_technical_analysis(self):
        """Calculate technical indicators"""
        hist_3m = self.t.history(period="3mo")
        hist_1y = self.t.history(period="1y")
        hist_2y = self.t.history(period="2y")

        close = hist_3m['Close']
        close_1y = hist_1y['Close']

        return {
            "rsi_14": self._calc_rsi(close, 14),
            "rsi_28": self._calc_rsi(close, 28),
            "macd": self._calc_macd(close),
            "sma_20": float(close.tail(20).mean()) if len(close) >= 20 else None,
            "sma_50": float(close_1y.tail(50).mean()) if len(close_1y) >= 50 else None,
            "sma_200": float(hist_2y['Close'].tail(200).mean()) if len(hist_2y) >= 200 else None,
            "ema_12": self._calc_ema(close, 12),
            "ema_26": self._calc_ema(close, 26),
            "bollinger_upper": self._calc_bollinger(close, 20, 2)[0],
            "bollinger_lower": self._calc_bollinger(close, 20, 2)[1],
            "atr_14": self._calc_atr(hist_3m, 14),
        }

    def _calc_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return float(100 - (100 / (1 + rs)).iloc[-1])

    def _calc_macd(self, prices, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1])
        }

    def _calc_ema(self, prices, period):
        return float(prices.ewm(span=period).mean().iloc[-1])

    def _calc_bollinger(self, prices, period=20, std_dev=2):
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return float(upper.iloc[-1]), float(lower.iloc[-1])

    def _calc_atr(self, hist, period=14):
        high_low = hist['High'] - hist['Low']
        high_close = np.abs(hist['High'] - hist['Close'].shift())
        low_close = np.abs(hist['Low'] - hist['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return float(true_range.rolling(window=period).mean().iloc[-1])

    # ========== Analyst Ratings ==========
    def get_analyst_consensus(self):
        """Analyst consensus ratings"""
        info = self.t.info
        recommendations = self.t.recommendations

        rec_summary = {}
        if recommendations is not None and not recommendations.empty:
            rec_summary = recommendations['To Grade'].value_counts().to_dict()

        return {
            "recommendation": info.get("recommendationKey"),
            "target_mean": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "recommendation_summary": rec_summary,
            "earnings_history": self.t.earnings_history.to_dict() if hasattr(self.t, 'earnings_history') and self.t.earnings_history is not None else None,
        }

    # ========== Options Data ==========
    def get_options_data(self):
        """Option chain data"""
        try:
            dates = self.t.options
            if not dates:
                return None

            # Get the nearest expiration date
            nearest_date = dates[0]
            chain = self.t.option_chain(nearest_date)

            return {
                "expiration": nearest_date,
                "calls": {
                    "implied_volatility": chain.calls['impliedVolatility'].head(10).tolist(),
                    "open_interest": chain.calls['openInterest'].head(10).tolist(),
                    "volume": chain.calls['volume'].head(10).tolist(),
                    "strike": chain.calls['strike'].head(10).tolist(),
                    "last_price": chain.calls['lastPrice'].head(10).tolist(),
                },
                "puts": {
                    "implied_volatility": chain.puts['impliedVolatility'].head(10).tolist(),
                    "open_interest": chain.puts['openInterest'].head(10).tolist(),
                    "volume": chain.puts['volume'].head(10).tolist(),
                    "strike": chain.puts['strike'].head(10).tolist(),
                    "last_price": chain.puts['lastPrice'].head(10).tolist(),
                },
                "iv_percentile": self.t.info.get("impliedVolatility"),
            }
        except Exception as e:
            return {"error": str(e)}

    # ========== Consolidated Output ==========
    def generate_analysis_data(self):
        """Generate complete analysis data"""
        return {
            "ticker": self.ticker,
            "generated_at": datetime.now().isoformat(),
            "quote": self.get_realtime_quote(),
            "financials": self.get_financials(),
            "technicals": self.get_technical_analysis(),
            "analyst": self.get_analyst_consensus(),
            "options": self.get_options_data(),
        }


# ========== Usage Examples ==========
if __name__ == "__main__":
    # Hong Kong - Tencent
    tool_hk = InvestmentAnalysisTool("00700.HK")
    data_hk = tool_hk.generate_analysis_data()
    print(json.dumps(data_hk, indent=2, ensure_ascii=False, default=str))

    # US - Apple
    tool_us = InvestmentAnalysisTool("AAPL")
    data_us = tool_us.generate_analysis_data()
    print(json.dumps(data_us, indent=2, ensure_ascii=False, default=str))

    # China A-shares - CATL
    tool_cn = InvestmentAnalysisTool("300750.SZ")
    data_cn = tool_cn.generate_analysis_data()
    print(json.dumps(data_cn, indent=2, ensure_ascii=False, default=str))
```

---

## 5. Quick Installation

```bash
# Install dependencies
pip install yfinance pandas numpy requests beautifulsoup4 lxml

# Run
python investment_analysis_tool.py
```

---

## 6. Data Source Comparison

| Data Source | Quotes | Financials | Technical Indicators | Options | 13F | Cost |
|------------|--------|-----------|---------------------|---------|-----|------|
| Yahoo Finance (yfinance) | Yes | Yes | Yes | Yes | No | Free |
| Alpha Vantage | Yes | Yes | Yes | No | No | Free tier |
| SEC EDGAR | No | Yes | No | No | Yes | Free |
| Finnhub | Yes | Yes | Yes | Yes | No | Free tier |
| Bloomberg | Yes | Yes | Yes | Yes | Yes | Paid |
| Wind | Yes | Yes | Yes | Yes | Yes | Paid |

---

## 7. Current State: Actual Implementation vs This Document's Design

Sections 1-6 were written during early design. The implementation in `src/augur/datasources/` evolved into a `DataProvider` abstract base class plus a provider chain. `default_providers()` builds the chain in this order: yfinance, then finnhub (only if `FINNHUB_API_KEY` is set), then alphavantage (only if `ALPHAVANTAGE_API_KEY` is set), then stooq. `_build_context_from_providers` in `data.py` uses the **first provider that returns non-empty data**; a provider that raises or returns empty is skipped and the next one is tried. Results are not merged across providers. If all fail, an empty `MarketContext` with `data_source="none"` and a `data_error` message is returned.

- **Stooq is currently broken**: the `/q/l/` quote endpoint returns HTTP 404 for any symbol and the `/q/d/l/` history endpoint serves an anti-bot JS challenge (see `stooq_provider.py`). It stays at the end of the chain at no cost, but does not currently return data.
- **Local dev environment (yfinance TLS)**: a `.venv` built on the macOS CommandLineTools python3.9 (Apple LibreSSL 2.8.3) makes yfinance's `curl_cffi` fail with `SSLError: invalid library`. This is a local toolchain issue, not an augur bug; rebuilding the venv on a Python linked against real OpenSSL fixes it.
- **Enabling Finnhub / Alpha Vantage needs no code change**: set the `FINNHUB_API_KEY` (free tier 60 req/min) and/or `ALPHAVANTAGE_API_KEY` (free tier 25 req/day, best as a fallback) environment variable. The provider chain reads only the process environment (`is_configured()` checks `os.environ`); there is no `.env` loader in `src/`, so `export` the variable or inject it from your process manager. The Dashboard Settings page stores `datasource_keys` but currently uses them only for the "test connection" button; they do not feed the provider chain.

**Candidate sources not integrated** (unverified, listed for future evaluation): Twelve Data (free tier, WebSocket; augur polls so the WebSocket advantage is unused), EODHD (narrow free tier, strong historical EOD), Financial Modeling Prep (free tier, financials/valuation coverage similar to Finnhub). IEX Cloud shut down in August 2024; ignore older recommendations for it.

## 8. Environment Variables and Caches (checked against `src/`, 2026-10)

| Variable | Purpose | Default |
|----------|---------|---------|
| `FINNHUB_API_KEY` | Non-empty adds Finnhub to the provider chain | unset = not in chain |
| `ALPHAVANTAGE_API_KEY` | Non-empty adds Alpha Vantage to the provider chain | unset = not in chain |
| `AUGUR_EDGAR_CONTACT_EMAIL` | Contact email in the SEC EDGAR `User-Agent` (`augur-agents (<email>)`) | unset: placeholder `augur-agents-user@example.com` plus a one-time warning; sustained placeholder use risks SEC rate limiting or an IP block |
| `AUGUR_DATA_DIR` | Data root; the EDGAR cache and `earnings_calendar.json` live under it | `~/.augur` |
| `AUGUR_EDGAR_GUIDANCE_EXTRACTION` | `1`/`true`/`yes` enables EDGAR guidance-text extraction | off |
| `AUGUR_WATCHLIST_FETCH_DELAY` | Seconds between per-ticker fetches in the scheduled watchlist job | `3.0` |

**Caches**:

- Quotes / fundamentals: in-process memory cache in `data.py`, TTL **180 seconds**, max 100 entries (evicts oldest by timestamp down to 80). `clear_cache()` clears it; `reset_providers_cache()` rebuilds the provider chain.
- EDGAR (on disk, `<data dir>/edgar_cache/`, default `~/.augur/edgar_cache/`): `company_tickers.json` (ticker-to-CIK map) TTL **7 days**; each CIK's companyfacts and `submissions_<cik>.json` TTL **24 hours**. If a refetch fails, `get_submissions` falls back to the stale cache file.

**EDGAR behavior** (`src/augur/consensus/edgar_fundamentals.py`): token-bucket rate limit of **10 req/s** (SEC's documented cap); 15-second HTTP timeout; one retry on transient network errors, no retry on HTTP 4xx. The CIK map comes from `https://www.sec.gov/files/company_tickers.json`; companyfacts and submissions come from `data.sec.gov`.

## 9. SEC 8-K Item 2.02 Earnings-Date Backfill

`src/augur/earnings_calendar.py` fills `<data dir>/earnings_calendar.json`, the calendar read by `augur earnings` and the watchlist earnings queue.

- **What it reads**: each ticker's EDGAR submissions, via the same EDGAR client (CIK lookup, User-Agent, rate limit and disk cache are all reused). Filings with form `8-K` or `8-K/A`, an `items` field containing `2.02` ("Results of Operations and Financial Condition") and a filing date on or before today become **historical earnings dates** (`confidence: "historical"`, `source: "sec_8k_2.02"`, with the `accession` number).
- **Estimated dates**: with at least 2 historical events, the median of the last (up to) 4 gaps between filings is added to the latest filing date to produce **at most one** next date, tagged `confidence: "estimated"`, `source: "estimated_from_8k_cadence"`. It is derived from filing cadence, not a company announcement, and is never marked `confirmed`.
- **Merging**: an existing entry for the same ticker and date wins; only missing dates are added, so hand-written entries are never overwritten. The file is written atomically and only when something was added. An unparsable calendar file aborts the backfill (it refuses to overwrite). A fetch failure for one ticker is recorded in the report and does not stop the others.
- **Command**: `augur earnings --backfill` (all watchlist tickers by default, or `-t AAPL -t MSFT`). It prints the number added per ticker and how many were estimated.

```bash
export AUGUR_EDGAR_CONTACT_EMAIL=you@example.com
augur earnings --backfill -t AAPL -t MSFT
augur earnings --days 30
```

---

*This document provides supplemental data integration options for investment analysis Skills. Integration is optional.*
