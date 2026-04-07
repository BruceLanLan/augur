# 📊 数据源API集成方案

本文档介绍如何为投资分析Skill集成实时数据API，覆盖股票行情、财务数据、期权数据、13F持仓等。

---

## 一、推荐API方案

### 1. Yahoo Finance API（免费，推荐）

**优点**：免费、数据全面、覆盖全球市场、无需申请

**集成方式**：使用 `yfinance` Python库

```python
import yfinance as yf

# 获取股票数据
ticker = yf.Ticker("00700.HK")

# 实时/历史价格
hist = ticker.history(period="1d")  # 当日价格
hist = ticker.history(period="1y")  # 1年历史

# 财务报表
income_stmt = ticker.financials        # 利润表
balance_sheet = ticker.balance_sheet    # 资产负债表
cash_flow = ticker.cashflow             # 现金流量表

# 推荐数据
recommendations = ticker.recommendations  # 分析师评级
analyst_price_targets = ticker.analyst_price_targets  # 目标价

# 期权数据
options = ticker.options                  # 到期日
calls = ticker.option_chain(date)[0]     # Call期权链
puts = ticker.option_chain(date)[1]      # Put期权链

# 关键统计
info = ticker.info  # PE、EPS、股息、50日均价等全部信息
```

### 2. Alpha Vantage（免费/付费）

**优点**：专业财务数据、GAAP/IFRS财报、实时价格

**申请**：https://www.alphavantage.co/ （免费API Key）

```python
import requests

API_KEY = "YOUR_FREE_KEY"
BASE_URL = "https://www.alphavantage.co/query"

# 股票报价
def get_quote(symbol):
    url = f"{BASE_URL}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
    return requests.get(url).json()

# 财报
def get_income_statement(symbol):
    url = f"{BASE_URL}?function=INCOME_STATEMENT&symbol={symbol}&apikey={API_KEY}"
    return requests.get(url).json()

# 关键技术指标
def get_overview(symbol):
    url = f"{BASE_URL}?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}"
    return requests.get(url).json()
```

### 3. SEC EDGAR API（免费，13F持仓）

**用途**：13F机构持仓、8-K重大事件、10-K/10-Q年报季报

```python
import requests

# 获取公司13F持仓（机构持仓）
def get_13f_filings(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": "Your Name your@email.com"}
    return requests.get(url, headers=headers).json()

# 获取最新13F
def get_latest_13f(cik):
    url = f"https://data.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F&owner=include&count=1"
    return requests.get(url, headers={"User-Agent": "Your Name your@email.com"}).text

# 搜索公司CIK
def search_company(company_name):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=companysearch&company={company_name}"
    return requests.get(url, headers={"User-Agent": "Your Name your@email.com"}).text
```

### 4. Finnhub（免费/付费）

**优点**：实时技术指标、蜡烛图、新闻情绪

**申请**：https://finnhub.io/ （免费tier可用）

```python
import requests

API_KEY = "YOUR_KEY"
BASE_URL = "https://finnhub.io/api/v1"

# 蜡烛图数据
def get_candles(symbol, resolution="D", from_time=None, to_time=None):
    url = f"{BASE_URL}/stock/candle?symbol={symbol}&resolution={resolution}&from={from_time}&to={to_time}&token={API_KEY}"
    return requests.get(url).json()

# 技术指标
def get_technical_indicators(symbol, indicator="sma", params={}):
    url = f"{BASE_URL}/scan/technical-indicator?symbol={symbol}&indicator={indicator}&token={API_KEY}"
    return requests.get(url).json()

# 分析师评级
def get_recommendations(symbol):
    url = f"{BASE_URL}/stock/recommendation?symbol={symbol}&token={API_KEY}"
    return requests.get(url).json()

# 收益日历
def get_earnings_calendar(from_date, to_date):
    url = f"{BASE_URL}/calendar/earnings?from={from_date}&to={to_date}&token={API_KEY}"
    return requests.get(url).json()
```

### 5. Crunchbase（VC/一级市场）

**用途**：融资历史、估值、创始人信息、投资方

```python
# Crunchbase API (需要付费，但有免费tier)
# https://data.crunchbase.com/docs

# 替代：使用公开的VC数据API
# Airbnb API: https://api.airbnb.com (需要申请)
```

---

## 二、集成到分析流程

### 数据获取工作流

```
分析请求 → 自动获取数据 → 数据处理 → 分析输出
              ↓
    ┌─────────┬─────────┬─────────┐
    ↓         ↓         ↓         ↓
  行情API   财报API   13F API   期权API
    ↓         ↓         ↓         ↓
  实时价格  财务数据  机构持仓  波动率
```

### Python数据获取脚本示例

```python
#!/usr/bin/env python3
"""
投资分析数据获取脚本
自动获取股票行情、财务数据、技术指标、分析师评级
"""

import yfinance as yf
import json
from datetime import datetime, timedelta

class StockDataFetcher:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.t = yf.Ticker(ticker)

    def get_price(self):
        """获取实时价格"""
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
        """获取技术指标"""
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
        """计算RSI"""
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
        """获取财务数据"""
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
        """获取分析师数据"""
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
        """获取所有数据"""
        return {
            "ticker": self.ticker,
            "timestamp": datetime.now().isoformat(),
            "price": self.get_price(),
            "technicals": self.get_technicals(),
            "financials": self.get_financials(),
            "analyst": self.get_analyst_data()
        }

# 使用示例
if __name__ == "__main__":
    fetcher = StockDataFetcher("00700.HK")
    data = fetcher.get_all_data()
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
```

---

## 三、13F机构持仓获取

```python
import requests
from bs4 import BeautifulSoup

def get_13f_holdings(company_name_or_cik):
    """
    获取13F机构持仓数据
    """
    # 如果输入的是公司名，先搜索CIK
    if not company_name_or_cik.isdigit():
        search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={company_name_or_cik}&type=13F&count=1"
        headers = {"User-Agent": "Your Name your@email.com"}
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 找到CIK...
        cik = soup.find('a', {'id': 'documentsButton'})['href'].split('CIK=')[1].split('&')[0]
    else:
        cik = company_name_or_cik

    # 获取最新的13F filing
    filings_url = f"https://data.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F&count=1"
    headers = {"User-Agent": "Your Name your@email.com", "Accept-Encoding": "gzip, deflate"}
    response = requests.get(filings_url, headers=headers)

    return response.text
```

---

## 四、完整数据分析工具

```python
#!/usr/bin/env python3
"""
完整投资分析数据工具
支持：行情、财务、技术指标、分析师评级、13F持仓、期权
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
        初始化
        market: US, HK, CN, JP, EU
        """
        self.ticker = ticker
        self.market = market
        self.t = yf.Ticker(ticker)

    # ========== 行情数据 ==========
    def get_realtime_quote(self):
        """实时行情"""
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

    # ========== 财务数据 ==========
    def get_financials(self):
        """完整财务报表"""
        return {
            "income_statement": self._safe_get_data(self.t.financials),
            "balance_sheet": self._safe_get_data(self.t.balance_sheet),
            "cash_flow": self._safe_get_data(self.t.cashflow),
            "quarterly_financials": self._safe_get_data(self.t.quarterly_financials),
        }

    def _safe_get_data(self, df):
        """安全获取DataFrame"""
        if df is None or df.empty:
            return None
        return df.to_dict()

    # ========== 技术指标 ==========
    def get_technical_analysis(self):
        """技术指标计算"""
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

    # ========== 分析师评级 ==========
    def get_analyst_consensus(self):
        """分析师共识评级"""
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

    # ========== 期权数据 ==========
    def get_options_data(self):
        """期权链数据"""
        try:
            dates = self.t.options
            if not dates:
                return None

            # 获取最近的到期日
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

    # ========== 整合输出 ==========
    def generate_analysis_data(self):
        """生成完整的分析数据"""
        return {
            "ticker": self.ticker,
            "generated_at": datetime.now().isoformat(),
            "quote": self.get_realtime_quote(),
            "financials": self.get_financials(),
            "technicals": self.get_technical_analysis(),
            "analyst": self.get_analyst_consensus(),
            "options": self.get_options_data(),
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 港股腾讯
    tool_hk = InvestmentAnalysisTool("00700.HK")
    data_hk = tool_hk.generate_analysis_data()
    print(json.dumps(data_hk, indent=2, ensure_ascii=False, default=str))

    # 美股苹果
    tool_us = InvestmentAnalysisTool("AAPL")
    data_us = tool_us.generate_analysis_data()
    print(json.dumps(data_us, indent=2, ensure_ascii=False, default=str))

    # A股宁德时代
    tool_cn = InvestmentAnalysisTool("300750.SZ")
    data_cn = tool_cn.generate_analysis_data()
    print(json.dumps(data_cn, indent=2, ensure_ascii=False, default=str))
```

---

## 五、快速安装

```bash
# 安装依赖
pip install yfinance pandas numpy requests beautifulsoup4 lxml

# 运行
python investment_analysis_tool.py
```

---

## 六、数据源对比

| 数据源 | 行情 | 财报 | 技术指标 | 期权 | 13F | 费用 |
|--------|------|------|----------|-------|------|------|
| Yahoo Finance (yfinance) | ✅ | ✅ | ✅ | ✅ | ❌ | 免费 |
| Alpha Vantage | ✅ | ✅ | ✅ | ❌ | ❌ | 免费tier |
| SEC EDGAR | ❌ | ✅ | ❌ | ❌ | ✅ | 免费 |
| Finnhub | ✅ | ✅ | ✅ | ✅ | ❌ | 免费tier |
| Bloomberg | ✅ | ✅ | ✅ | ✅ | ✅ | 付费 |
| Wind | ✅ | ✅ | ✅ | ✅ | ✅ | 付费 |

---

*本文档为投资分析Skill的数据补充方案，可选择性集成。*
