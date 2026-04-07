#!/usr/bin/env python3
"""
投资分析数据获取脚本
使用Yahoo Finance API获取实时行情、财务数据、技术指标、期权数据

安装依赖：
    pip install yfinance pandas numpy requests beautifulsoup4 lxml

使用方式：
    python data_fetcher.py 00700.HK
    python data_fetcher.py AAPL
    python data_fetcher.py 300750.SZ
"""

import sys
import json
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("请先安装依赖：pip install yfinance pandas numpy")
    sys.exit(1)


class StockDataFetcher:
    """股票数据获取器"""

    SUPPORTED_TICKERS = {
        "00700.HK": {"name": "腾讯控股", "market": "HK"},
        "0700.HK": {"name": "腾讯控股", "market": "HK"},
        "AAPL": {"name": "Apple", "market": "US"},
        "MSFT": {"name": "Microsoft", "market": "US"},
        "GOOGL": {"name": "Google", "market": "US"},
        "AMZN": {"name": "Amazon", "market": "US"},
        "TSLA": {"name": "Tesla", "market": "US"},
        "NVDA": {"name": "NVIDIA", "market": "US"},
        "META": {"name": "Meta", "market": "US"},
        "300750.SZ": {"name": "宁德时代", "market": "CN"},
        "600519.SH": {"name": "贵州茅台", "market": "CN"},
    }

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.t = yf.Ticker(self.ticker)
        self.info = None
        self.hist = None

    def fetch_all(self):
        """获取所有数据"""
        try:
            self.info = self.t.info
            self.hist = {
                "1d": self.t.history(period="1d"),
                "5d": self.t.history(period="5d"),
                "1mo": self.t.history(period="1mo"),
                "3mo": self.t.history(period="3mo"),
                "6mo": self.t.history(period="6mo"),
                "1y": self.t.history(period="1y"),
                "2y": self.t.history(period="2y"),
                "5y": self.t.history(period="5y"),
            }
            return True
        except Exception as e:
            print(f"获取数据失败: {e}")
            return False

    def get_quote(self):
        """实时行情"""
        if not self.info:
            return {}

        return {
            "symbol": self.ticker,
            "name": self.info.get("longName") or self.info.get("shortName"),
            "price": self.info.get("currentPrice") or self.info.get("regularMarketPrice"),
            "currency": self.info.get("currency"),
            "exchange": self.info.get("exchange"),
            "market_time": self.info.get("marketTime"),
            "change": self.info.get("regularMarketChange"),
            "change_pct": self.info.get("regularMarketChangePercent"),
            "open": self.info.get("regularMarketOpen"),
            "high": self.info.get("regularMarketDayHigh"),
            "low": self.info.get("regularMarketDayLow"),
            "volume": self.info.get("regularMarketVolume"),
            "avg_volume": self.info.get("averageVolume"),
            "market_cap": self.info.get("marketCap"),
            "pe_ratio": self.info.get("trailingPE"),
            "forward_pe": self.info.get("forwardPE"),
            "eps": self.info.get("trailingEps"),
            "forward_eps": self.info.get("forwardEps"),
            "dividend": self.info.get("dividendRate"),
            "dividend_yield": self.info.get("dividendYield"),
            "beta": self.info.get("beta"),
            "52w_high": self.info.get("fiftyTwoWeekHigh"),
            "52w_low": self.info.get("fiftyTwoWeekLow"),
            "50d_ma": self.info.get("fiftyDayAverage"),
            "200d_ma": self.info.get("twoHundredDayAverage"),
        }

    def get_price_history(self):
        """历史价格"""
        if not self.hist or self.hist.get("1y") is None:
            return {}

        hist_1y = self.hist["1y"]
        hist_2y = self.hist["2y"] if self.hist.get("2y") is not None else hist_1y

        return {
            "current_price": float(hist_1y['Close'].iloc[-1]) if len(hist_1y) > 0 else None,
            "1y_high": float(hist_1y['High'].max()) if len(hist_1y) > 0 else None,
            "1y_low": float(hist_1y['Low'].min()) if len(hist_1y) > 0 else None,
            "1y_return": float((hist_1y['Close'].iloc[-1] / hist_1y['Close'].iloc[0] - 1) * 100) if len(hist_1y) > 0 else None,
            "6m_return": float((self.hist["6m"]['Close'].iloc[-1] / self.hist["6m"]['Close'].iloc[0] - 1) * 100) if self.hist.get("6m") is not None and len(self.hist["6m"]) > 0 else None,
            "3m_return": float((self.hist["3mo"]['Close'].iloc[-1] / self.hist["3mo"]['Close'].iloc[0] - 1) * 100) if self.hist.get("3mo") is not None and len(self.hist["3mo"]) > 0 else None,
        }

    def get_technicals(self):
        """技术指标"""
        if not self.hist or self.hist.get("3mo") is None:
            return {}

        hist = self.hist["3mo"]
        if len(hist) < 20:
            return {"error": "数据不足，无法计算技术指标"}

        close = hist['Close']
        high = hist['High']
        low = hist['Low']

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = float((100 - (100 / (1 + rs))).iloc[-1])

        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9).mean()
        macd_hist = macd_line - signal_line

        # 均线
        sma_20 = float(close.tail(20).mean()) if len(close) >= 20 else None
        sma_50 = float(close.tail(50).mean()) if len(close) >= 50 else None

        # 布林带
        bb_mid = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        bb_upper = bb_mid + (bb_std * 2)
        bb_lower = bb_mid - (bb_std * 2)

        # ATR
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = float(tr.rolling(window=14).mean().iloc[-1])

        return {
            "rsi_14": round(rsi_14, 2),
            "rsi_status": "超买" if rsi_14 > 70 else "超卖" if rsi_14 < 30 else "中性",
            "macd": {
                "macd_line": float(macd_line.iloc[-1]),
                "signal_line": float(signal_line.iloc[-1]),
                "histogram": float(macd_hist.iloc[-1]),
                "signal": "金叉" if macd_line.iloc[-1] > signal_line.iloc[-1] else "死叉",
            },
            "sma": {
                "sma_20": round(sma_20, 2) if sma_20 else None,
                "sma_50": round(sma_50, 2) if sma_50 else None,
            },
            "bollinger": {
                "upper": float(bb_upper.iloc[-1]),
                "mid": float(bb_mid.iloc[-1]),
                "lower": float(bb_lower.iloc[-1]),
                "bandwidth": float((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_mid.iloc[-1] * 100) if bb_mid.iloc[-1] != 0 else None,
            },
            "atr_14": round(atr_14, 2),
        }

    def get_financials(self):
        """财务报表"""
        try:
            income = self.t.financials
            balance = self.t.balance_sheet
            cashflow = self.t.cashflow

            def safe_get_value(df, row_name, col=0):
                if df is None or df.empty:
                    return None
                if row_name not in df.index:
                    return None
                try:
                    val = df.loc[row_name].iloc[col]
                    return float(val) if pd.notna(val) else None
                except:
                    return None

            # 最近4个季度
            quarterly = self.t.quarterly_financials
            q_revenue = None
            q_net_income = None
            if quarterly is not None and not quarterly.empty:
                q_revenue = safe_get_value(quarterly, 'Total Revenue', 0)
                q_net_income = safe_get_value(quarterly, 'Net Income', 0)

            return {
                "annual": {
                    "revenue": safe_get_value(income, 'Total Revenue'),
                    "gross_profit": safe_get_value(income, 'Gross Profit'),
                    "operating_income": safe_get_value(income, 'Operating Income'),
                    "net_income": safe_get_value(income, 'Net Income'),
                    "ebitda": safe_get_value(income, 'EBITDA'),
                    "eps": safe_get_value(income, 'BasicEPS'),
                    "diluted_eps": safe_get_value(income, 'DilutedEPS'),
                },
                "quarterly": {
                    "revenue": q_revenue,
                    "net_income": q_net_income,
                },
                "balance_sheet": {
                    "total_assets": safe_get_value(balance, 'Total Assets'),
                    "total_liabilities": safe_get_value(balance, 'Total Liabilities'),
                    "total_equity": safe_get_value(balance, 'Total Stockholder Equity'),
                    "cash": safe_get_value(balance, 'Cash'),
                    "long_term_debt": safe_get_value(balance, 'Long Term Debt'),
                },
                "cash_flow": {
                    "operating_cashflow": safe_get_value(cashflow, 'Operating Cash Flow'),
                    "free_cashflow": safe_get_value(cashflow, 'Free Cash Flow'),
                    "capital_expenditure": safe_get_value(cashflow, 'Capital Expenditures'),
                },
            }
        except Exception as e:
            return {"error": str(e)}

    def get_analyst_data(self):
        """分析师评级"""
        if not self.info:
            return {}

        recs = None
        try:
            recs = self.t.recommendations
        except:
            pass

        recommendations_summary = {}
        if recs is not None and not recs.empty:
            try:
                recommendations_summary = recs['To Grade'].value_counts().head(5).to_dict()
            except:
                pass

        return {
            "recommendation_key": self.info.get("recommendationKey"),
            "target_mean": self.info.get("targetMeanPrice"),
            "target_high": self.info.get("targetHighPrice"),
            "target_low": self.info.get("targetLowPrice"),
            "analyst_count": self.info.get("numberOfAnalystOpinions"),
            "recommendations_summary": recommendations_summary,
        }

    def get_options(self):
        """期权数据"""
        try:
            dates = self.t.options
            if not dates or len(dates) == 0:
                return {"available": False, "reason": "无期权数据"}

            nearest_date = dates[0]
            chain = self.t.option_chain(nearest_date)

            def safe_list(series, n=5):
                if series is None or len(series) == 0:
                    return []
                return series.head(n).tolist()

            return {
                "available": True,
                "expiration": nearest_date,
                "implied_volatility": self.info.get("impliedVolatility"),
                "calls": {
                    "strike": safe_list(chain.calls['strike']),
                    "last_price": safe_list(chain.calls['lastPrice']),
                    "bid": safe_list(chain.calls['bid']),
                    "ask": safe_list(chain.calls['ask']),
                    "volume": safe_list(chain.calls['volume']),
                    "open_interest": safe_list(chain.calls['openInterest']),
                    "implied_volatility": safe_list(chain.calls['impliedVolatility']),
                },
                "puts": {
                    "strike": safe_list(chain.puts['strike']),
                    "last_price": safe_list(chain.puts['lastPrice']),
                    "bid": safe_list(chain.puts['bid']),
                    "ask": safe_list(chain.puts['ask']),
                    "volume": safe_list(chain.puts['volume']),
                    "open_interest": safe_list(chain.puts['openInterest']),
                    "implied_volatility": safe_list(chain.puts['impliedVolatility']),
                },
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_all_data(self):
        """获取完整数据"""
        if not self.fetch_all():
            return {"error": "数据获取失败"}

        return {
            "ticker": self.ticker,
            "market": self.SUPPORTED_TICKERS.get(self.ticker, {}).get("market", "UNKNOWN"),
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": self.get_quote(),
            "price_history": self.get_price_history(),
            "technicals": self.get_technicals(),
            "financials": self.get_financials(),
            "analyst": self.get_analyst_data(),
            "options": self.get_options(),
        }


def main():
    if len(sys.argv) < 2:
        print("用法: python data_fetcher.py <TICKER>")
        print("示例: python data_fetcher.py 00700.HK")
        print("       python data_fetcher.py AAPL")
        print("       python data_fetcher.py 300750.SZ")
        sys.exit(1)

    ticker = sys.argv[1]
    print(f"\n正在获取 {ticker} 数据...\n")

    fetcher = StockDataFetcher(ticker)
    data = fetcher.get_all_data()

    if "error" in data and data["error"]:
        print(f"错误: {data['error']}")
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
