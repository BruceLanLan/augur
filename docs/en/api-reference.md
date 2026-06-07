# Augur API Reference / API 参考文档

> Version: v8.2.0

## Base URL / 基础地址

- Local: `http://localhost:8000`
- All endpoints return JSON unless otherwise noted
- 所有接口返回 JSON 格式 (除非另行说明)

---

## Analysis / 分析

### GET /api/analyze/{ticker}

**Description / 说明:**
Run a full multi-agent analysis for a given ticker. All 18 persona agents evaluate the stock and produce a weighted consensus signal.

对指定标的运行 18 位投资大师全量分析，返回加权共识信号。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| ticker | string | path | Stock ticker symbol (e.g., AAPL, NVDA, 0700.HK) |

**Response / 响应:**
```json
{
  "ticker": "AAPL",
  "signal": "BUY",
  "score": 7.2,
  "kelly_position": 0.15,
  "confidence": 0.82,
  "agents": [
    {
      "id": "buffett",
      "name": "Warren Buffett",
      "signal": "BUY",
      "score": 8,
      "reasoning": "..."
    }
  ],
  "consensus": {
    "buy_count": 12,
    "sell_count": 3,
    "hold_count": 3
  }
}
```

---

### GET /api/report/{ticker}

**Description / 说明:**
Retrieve a cached analysis report for a ticker (if available).

获取已缓存的分析报告 (如果存在)。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| ticker | string | path | Stock ticker symbol |

**Response / 响应:**
```json
{
  "ticker": "AAPL",
  "report": "# Analysis Report for AAPL\n...",
  "generated_at": "2026-06-01T10:00:00Z",
  "format": "markdown"
}
```

---

### POST /api/report/{ticker}

**Description / 说明:**
Generate a report from pre-computed analysis data for the given ticker.

基于已有分析数据生成指定标的的完整报告。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| ticker | string | path | Stock ticker symbol |

**Response / 响应:**
```json
{
  "ticker": "AAPL",
  "report": "# Full Report...",
  "generated_at": "2026-06-01T10:00:00Z"
}
```

---

## Scanner / 扫描器

### POST /api/scanner/run

**Description / 说明:**
Run batch analysis on multiple tickers. Returns a heatmap-style scoring matrix from all 18 persona agents.

批量扫描多个标的，返回 18 位大师的 heatmap 评分矩阵。

**Request Body / 请求体:**
```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA"],
  "preset": null
}
```

Or use a preset:
```json
{
  "preset": "tech_giants"
}
```

Available presets / 可用预设: `tech_giants` (科技巨头), `china_adr` (中概股), `crypto` (加密货币)

**Response / 响应:**
```json
{
  "results": [
    {
      "ticker": "AAPL",
      "signal": "BUY",
      "score": 7.5,
      "scores": {
        "buffett": 8,
        "dalio": 7,
        "lynch": 8,
        "soros": 6
      }
    }
  ],
  "scanned_at": "2026-06-01T10:00:00Z",
  "count": 4
}
```

---

## Market Data / 市场数据

### GET /api/market-overview

**Description / 说明:**
Get market overview data including major indices and key metrics. Supports ETag + 304 conditional requests for performance.

获取市场概览数据 (主要指数与关键指标)。支持 ETag + 304 条件请求。

**Headers:**
- `If-None-Match`: (optional) Previous ETag value for conditional request

**Response / 响应:**
```json
{
  "indices": {
    "SP500": {"value": 5200.5, "change_pct": 0.5},
    "NASDAQ": {"value": 16500.2, "change_pct": 0.8},
    "DJI": {"value": 39000.1, "change_pct": 0.3}
  },
  "updated_at": "2026-06-01T10:00:00Z"
}
```

---

### GET /api/hot-tickers

**Description / 说明:**
Get trending/hot tickers with recent activity. Supports ETag + 304 conditional requests.

获取热门标的列表。支持 ETag + 304 条件请求。

**Response / 响应:**
```json
{
  "tickers": [
    {"ticker": "NVDA", "name": "NVIDIA", "change_pct": 3.2, "volume": "85M"},
    {"ticker": "AAPL", "name": "Apple", "change_pct": -0.5, "volume": "62M"}
  ]
}
```

---

### GET /api/fetch/{ticker}

**Description / 说明:**
Fetch raw market data for a specific ticker from configured data sources.

从数据源获取指定标的的原始市场数据。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| ticker | string | path | Stock ticker symbol |

**Response / 响应:**
```json
{
  "ticker": "AAPL",
  "price": 195.5,
  "pe_ratio": 28.5,
  "market_cap": "3.0T",
  "volume": "55M",
  "change_pct": 1.2,
  "52w_high": 199.0,
  "52w_low": 140.0
}
```

---

### GET /api/search?q={query}

**Description / 说明:**
Search for tickers by name or symbol.

按名称或代码搜索标的。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| q | string | query | Search query (min 1 character) |

**Response / 响应:**
```json
{
  "results": [
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"ticker": "AAPL.L", "name": "Apple Inc. (London)", "exchange": "LSE"}
  ]
}
```

---

### GET /api/market-movers

**Description / 说明:**
Get top 5 gainers and losers in the market today.

获取今日涨跌幅领先标的（Top 5 领涨 / Top 5 领跌）。

**Response / 响应:**
```json
{
  "gainers": [
    {"ticker": "XYZ", "name": "XYZ Corp", "price": 45.2, "change_pct": 12.5},
    {"ticker": "ABC", "name": "ABC Inc", "price": 88.0, "change_pct": 9.8}
  ],
  "losers": [
    {"ticker": "DEF", "name": "DEF Ltd", "price": 22.1, "change_pct": -8.3},
    {"ticker": "GHI", "name": "GHI Co", "price": 15.5, "change_pct": -6.7}
  ],
  "updated_at": "2026-06-01T10:00:00Z"
}
```

---

### GET /api/crypto-overview

**Description / 说明:**
Get real-time price overview for major cryptocurrencies (BTC, ETH, SOL, DOGE, XRP).

获取主要加密货币（BTC, ETH, SOL, DOGE, XRP）的实时行情总览。

**Response / 响应:**
```json
{
  "crypto": [
    {"symbol": "BTC-USD", "name": "Bitcoin", "price": 67500.0, "change_pct": 2.1, "market_cap": "1.3T"},
    {"symbol": "ETH-USD", "name": "Ethereum", "price": 3450.0, "change_pct": 1.5, "market_cap": "415B"},
    {"symbol": "SOL-USD", "name": "Solana", "price": 155.0, "change_pct": 4.2, "market_cap": "68B"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "price": 0.12, "change_pct": -0.8, "market_cap": "17B"},
    {"symbol": "XRP-USD", "name": "XRP", "price": 0.52, "change_pct": 0.3, "market_cap": "28B"}
  ],
  "updated_at": "2026-06-01T10:00:00Z"
}
```

---

### GET /api/commodities

**Description / 说明:**
Get real-time prices for major commodities (Gold, Silver, Oil WTI, Natural Gas).

获取主要大宗商品（黄金、白银、WTI 原油、天然气）实时行情。

**Response / 响应:**
```json
{
  "commodities": [
    {"symbol": "GC=F", "name": "Gold", "price": 2350.5, "change_pct": 0.8, "unit": "USD/oz"},
    {"symbol": "SI=F", "name": "Silver", "price": 29.8, "change_pct": 1.2, "unit": "USD/oz"},
    {"symbol": "CL=F", "name": "Oil WTI", "price": 78.5, "change_pct": -0.5, "unit": "USD/bbl"},
    {"symbol": "NG=F", "name": "Natural Gas", "price": 2.35, "change_pct": -1.1, "unit": "USD/MMBtu"}
  ],
  "updated_at": "2026-06-01T10:00:00Z"
}
```

---

### GET /api/treasury-rates

**Description / 说明:**
Get current US Treasury yield rates (2Y, 5Y, 10Y, 30Y).

获取美国国债收益率（2 年期、5 年期、10 年期、30 年期）。

**Response / 响应:**
```json
{
  "rates": [
    {"maturity": "2Y", "symbol": "^IRX", "yield_pct": 4.72},
    {"maturity": "5Y", "symbol": "^FVX", "yield_pct": 4.35},
    {"maturity": "10Y", "symbol": "^TNX", "yield_pct": 4.48},
    {"maturity": "30Y", "symbol": "^TYX", "yield_pct": 4.62}
  ],
  "updated_at": "2026-06-01T10:00:00Z"
}
```

---

## Personas / 投资人

### GET /api/personas

**Description / 说明:**
List all available investor persona agents with their profiles.

获取所有可用的投资人 Agent 列表及其简介。

**Response / 响应:**
```json
{
  "personas": [
    {
      "id": "buffett",
      "name": "Warren Buffett",
      "name_zh": "沃伦·巴菲特",
      "style": "Value Investing",
      "philosophy": "Buy wonderful companies at fair prices",
      "school": "value"
    }
  ],
  "count": 18
}
```

---

### GET /api/persona/{agent_id}

**Description / 说明:**
Get detailed information for a specific persona agent.

获取指定投资人 Agent 的详细信息。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| agent_id | string | path | Agent identifier (e.g., buffett, dalio, lynch) |

**Response / 响应:**
```json
{
  "id": "buffett",
  "name": "Warren Buffett",
  "name_zh": "沃伦·巴菲特",
  "style": "Value Investing",
  "philosophy": "Buy wonderful companies at fair prices",
  "key_metrics": ["ROE", "moat", "management_quality"],
  "famous_holdings": ["AAPL", "KO", "BRK"]
}
```

---

### POST /api/custom-persona

**Description / 说明:**
Create a custom persona agent with user-defined parameters.

创建自定义投资人 Agent。

**Request Body / 请求体:**
```json
{
  "name": "My Custom Investor",
  "style": "Growth at Reasonable Price",
  "philosophy": "Find companies with strong moats growing at 20%+",
  "key_metrics": ["revenue_growth", "PE_ratio", "market_share"]
}
```

**Response / 响应:**
```json
{
  "id": "custom_1",
  "name": "My Custom Investor",
  "created": true
}
```

---

### GET /api/schema/persona

**Description / 说明:**
Get the JSON schema for creating custom personas.

获取自定义 Persona 的 JSON Schema。

**Response / 响应:**
```json
{
  "type": "object",
  "required": ["name", "style", "philosophy"],
  "properties": {
    "name": {"type": "string"},
    "style": {"type": "string"},
    "philosophy": {"type": "string"},
    "key_metrics": {"type": "array", "items": {"type": "string"}}
  }
}
```

---

## Configuration / 配置

### GET /api/config

**Description / 说明:**
Get current system configuration (API keys are masked for security).

获取当前系统配置 (API Key 已脱敏处理)。

**Response / 响应:**
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "***sk-xxxx"
  },
  "datasources": {
    "primary": "yfinance",
    "finnhub_key": "***xxxx"
  }
}
```

---

### PUT /api/config

**Description / 说明:**
Update system configuration.

更新系统配置。

**Request Body / 请求体:**
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "sk-..."
  }
}
```

**Response / 响应:**
```json
{"status": "ok", "message": "Configuration updated"}
```

---

### GET /api/config/persona/{agent_id}

**Description / 说明:**
Get LLM configuration for a specific persona agent.

获取指定 Agent 的 LLM 配置。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| agent_id | string | path | Agent identifier |

**Response / 响应:**
```json
{
  "agent_id": "buffett",
  "model": "gpt-4",
  "temperature": 0.3
}
```

---

### PUT /api/config/persona/{agent_id}

**Description / 说明:**
Update LLM configuration for a specific persona agent.

更新指定 Agent 的 LLM 配置。

**Request Body / 请求体:**
```json
{
  "model": "gpt-4o",
  "temperature": 0.5
}
```

---

### GET /api/models

**Description / 说明:**
List available LLM models.

列出可用的 LLM 模型列表。

**Response / 响应:**
```json
{
  "models": ["gpt-4", "gpt-4o", "gpt-3.5-turbo", "claude-3-sonnet"]
}
```

---

### GET /api/config/export

**Description / 说明:**
Export full configuration as JSON for backup.

导出完整配置 (JSON 格式，用于备份)。

**Response / 响应:**
Returns a JSON file containing all configuration data.

---

### POST /api/config/import

**Description / 说明:**
Import configuration from a JSON backup.

从 JSON 备份导入配置。

**Request Body / 请求体:**
Full configuration JSON (same format as export).

---

## Notifications / 通知

### POST /api/notifications/test

**Description / 说明:**
Send a test notification to verify channel configuration.

发送测试通知以验证通道配置是否正常。

**Request Body / 请求体:**
```json
{
  "channel": "telegram",
  "config": {
    "bot_token": "123456:ABC...",
    "chat_id": "987654321"
  }
}
```

Supported channels / 支持的通道: `telegram`, `slack`, `lark`, `wechat`

**Response / 响应:**
```json
{"status": "ok", "message": "Test notification sent successfully"}
```

---

### GET /api/notifications/config

**Description / 说明:**
Get current notification configuration.

获取当前通知配置。

**Response / 响应:**
```json
{
  "channels": {
    "telegram": {"enabled": true, "chat_id": "***4321"},
    "slack": {"enabled": false}
  },
  "alert_threshold": 7.0
}
```

---

### POST /api/notifications/config

**Description / 说明:**
Save notification configuration.

保存通知配置 (写入 config/notifications.yaml)。

**Request Body / 请求体:**
```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "123456:ABC...",
      "chat_id": "987654321"
    }
  },
  "alert_threshold": 7.5
}
```

**Response / 响应:**
```json
{"status": "ok", "message": "Notification config saved"}
```

---

## Watchlist / 自选股

### GET /api/watchlist

**Description / 说明:**
Get the user's watchlist of tracked tickers.

获取用户的自选股列表。

**Response / 响应:**
```json
{
  "watchlist": [
    {"ticker": "AAPL", "added_at": "2026-05-01"},
    {"ticker": "NVDA", "added_at": "2026-05-15"}
  ]
}
```

---

### POST /api/watchlist/add

**Description / 说明:**
Add a ticker to the watchlist.

添加标的到自选股列表。

**Request Body / 请求体:**
```json
{"ticker": "TSLA"}
```

**Response / 响应:**
```json
{"status": "ok", "ticker": "TSLA", "message": "Added to watchlist"}
```

---

### DELETE /api/watchlist/{ticker}

**Description / 说明:**
Remove a ticker from the watchlist.

从自选股列表移除标的。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| ticker | string | path | Ticker to remove |

**Response / 响应:**
```json
{"status": "ok", "message": "Removed from watchlist"}
```

---

### POST /api/watchlist/run

**Description / 说明:**
Run analysis on all tickers in the watchlist.

对自选股列表中的所有标的运行分析。

**Response / 响应:**
```json
{
  "results": [
    {"ticker": "AAPL", "signal": "BUY", "score": 7.5},
    {"ticker": "NVDA", "signal": "BUY", "score": 8.1}
  ]
}
```

---

## Backtest / 回测

### GET /api/backtest/run

**Description / 说明:**
Run a backtest simulation with specified parameters.

运行回测模拟。

**Parameters / 参数:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| ticker | string | query | Ticker to backtest |
| days | int | query | Number of days to backtest (default: 90) |
| initial_capital | float | query | Initial capital in USD (default: 100000) |
| strategy | string | query | Position strategy: equal/kelly/fixed (default: kelly) |

**Response / 响应:**
```json
{
  "ticker": "AAPL",
  "period_days": 90,
  "initial_capital": 100000,
  "final_value": 112500,
  "annual_return": 0.52,
  "max_drawdown": -0.08,
  "sharpe_ratio": 2.1,
  "win_rate": 0.67,
  "trades": [
    {"date": "2026-03-01", "action": "BUY", "price": 175.0},
    {"date": "2026-04-15", "action": "SELL", "price": 192.0}
  ]
}
```

---

### GET /api/backtest/leaderboard

**Description / 说明:**
Get the persona performance leaderboard from backtests.

获取各投资人 Agent 的回测排行榜。

**Response / 响应:**
```json
{
  "leaderboard": [
    {"agent_id": "buffett", "name": "Warren Buffett", "annual_return": 0.25, "sharpe": 1.8},
    {"agent_id": "lynch", "name": "Peter Lynch", "annual_return": 0.22, "sharpe": 1.6}
  ]
}
```

---

## v8 Features / v8 新功能端点

### POST /api/chat

向投资大师提问，返回 persona 风格的回复。

**Request body:**
```json
{
  "message": "What do you think about NVDA?",
  "agent_id": "buffett"   // 可选，不填则随机选取
}
```

**Response:**
```json
{
  "agent_id": "buffett",
  "agent_name": "Warren Buffett",
  "response": "Well, let me think about this...",
  "topic": "value",
  "timestamp": 1234567890.0
}
```

支持的 `agent_id`：`buffett` · `graham` · `lynch` · `dalio` · `munger` · `soros` · `marks` · `cathie_wood` · `serenity` · `thiel` · `duan_yongping`

---

### POST /api/optimize

Markowitz 均值方差组合优化。

**Request body:**
```json
{
  "tickers": ["AAPL", "NVDA", "MSFT"],
  "risk_free_rate": 0.02
}
```

**Response:**
```json
{
  "status": "ok",
  "data_source": "live",
  "tickers": ["AAPL", "NVDA", "MSFT"],
  "portfolio": {
    "weights": {"AAPL": 0.45, "NVDA": 0.35, "MSFT": 0.20},
    "expected_return": 0.012,
    "volatility": 0.018,
    "sharpe_ratio": 0.65
  }
}
```

`data_source` 为 `live`（yfinance 真实数据）、`partial`（部分真实）或 `mock`（全降级）。

---

### GET /api/sentiment/{ticker}

获取社交情绪分析（StockTwits + Reddit 可选 + X mock）。

**Response:**
```json
{
  "ticker": "NVDA",
  "overall_score": 0.32,
  "sources": {
    "stocktwits_score": 0.45,
    "reddit_score": 0.28,
    "x_score": -0.12
  },
  "volume": 8420,
  "trending": false,
  "data_source": "partial"
}
```

`overall_score` 范围 `[-1.0, +1.0]`，正数看多，负数看空。

---

### POST /api/compare

多大师对同一股票独立分析横向对比。

**Request body:**
```json
{
  "ticker": "AAPL",
  "agent_ids": ["buffett", "munger", "graham"]
}
```

`agent_ids` 须 2-5 个，不可重复。

**Response:**
```json
{
  "ticker": "AAPL",
  "agent_count": 3,
  "agents": [
    {
      "agent_id": "buffett",
      "agent_name": "Warren Buffett",
      "signal": "bullish",
      "score": 7.5,
      "confidence": 0.78,
      "key_findings": ["..."],
      "risks": ["..."]
    }
  ],
  "timestamp": "2026-06-02T00:00:00Z"
}
```

---

### POST /api/debate

多大师顺序辩论，每位回应前者。

**Request body:**
```json
{
  "ticker": "TSLA",
  "agent_ids": ["buffett", "cathie_wood"]
}
```

`agent_ids` 须 2-4 个。

**Response:**
```json
{
  "ticker": "TSLA",
  "rounds": [
    {
      "agent_id": "buffett",
      "agent_name": "Warren Buffett",
      "signal": "bearish",
      "score": 4.2,
      "confidence": 0.65,
      "reasoning": "...",
      "round": 1
    },
    {
      "agent_id": "cathie_wood",
      "agent_name": "Cathie Wood",
      "signal": "bullish",
      "score": 8.8,
      "confidence": 0.92,
      "reasoning": "[对前者观点的回应] ...",
      "round": 2
    }
  ],
  "summary": "辩论结束: 1/2 位投资人看多 TSLA。",
  "timestamp": "2026-06-02T00:00:00Z"
}
```

---

### GET /api/history

获取分析历史列表。支持分页。

**Query parameters:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | int | 返回条数（默认 50，非分页模式） |
| `page` | int | 页码（启用分页模式） |
| `per_page` | int | 每页条数（默认 20） |

**Response（非分页）:**
```json
{"records": [...], "count": 12}
```

**Response（分页）:**
```json
{"items": [...], "total": 120, "page": 2, "per_page": 20, "pages": 6}
```

---

### DELETE /api/history

清空所有历史记录。返回 `{"status": "ok", "deleted": 42}`

### GET /api/history/{history_id}

获取单条历史记录。

### DELETE /api/history/{history_id}

删除单条历史记录。

---

### GET /api/rules

列出所有告警规则。

### POST /api/rules

创建告警规则。

**Request body:**
```json
{
  "name": "NVDA 看多信号",
  "conditions": [
    {"field": "signal", "operator": "eq", "value": "bullish"},
    {"field": "score", "operator": "gte", "value": 7.5}
  ],
  "actions": [
    {"type": "telegram", "message": "NVDA 看多，评分 {score}"}
  ],
  "enabled": true
}
```

### DELETE /api/rules/{rule_id}

删除指定规则。

---

### WebSocket /ws/analyze/{ticker}

流式推送 18 位大师的分析进度，每个 agent 完成后立即发送，最后发送共识。

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/analyze/AAPL');
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'agent') {
    // 单个 agent 结果
    console.log(data.agent_name, data.signal, data.score, data.progress);
  } else if (data.type === 'consensus') {
    // 最终共识
    console.log('Consensus:', data.signal, data.score);
  }
};
```

每条消息结构：

| `type` | 字段 |
|--------|------|
| `agent` | `agent_id`, `agent_name`, `signal`, `score`, `confidence`, `reasoning`, `progress` (如 "5/18") |
| `consensus` | 同 `/api/analyze/{ticker}` 的共识对象 |
| `error` | `message` |

---

## v9 Features

### POST /api/committee

Convene an investment committee: selected masters analyze independently, returning individual opinions + weighted verdict. Session is automatically saved to history.

**Request body:**

```json
{
  "ticker": "AAPL",
  "question": "Is the moat narrowing?",
  "agents": ["buffett", "munger", "duan_yongping"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ticker` | string | ✅ | Stock ticker (1-15 chars) |
| `question` | string | ✅ | The core question for the committee |
| `agents` | string[] | ❌ | List of agent IDs; empty = all 18 |

**Response:**

```json
{
  "status": "ok",
  "ticker": "AAPL",
  "history_id": "20260607_143022_000000_AAPL",
  "opinions": [...],
  "verdict": {
    "signal": "bullish",
    "score": 7.6,
    "confidence": 0.78,
    "kelly_pct": 12.0,
    "vote": {"bullish": 2, "neutral": 1, "bearish": 0}
  },
  "session_type": "committee"
}
```

**Error codes:** `400` invalid ticker | `400` question required | `429` rate limit

---

## System / 系统

### GET /health

**Description / 说明:**
Basic health check endpoint.

基础健康检查接口。

**Response / 响应:**
```json
{"status": "ok"}
```

---

### GET /api/health

**Description / 说明:**
Extended health check with system details including datasource reachability, cache status, uptime, and version.

扩展健康检查，包含数据源可达性、缓存状态、运行时间和版本号。

**Response / 响应:**
```json
{
  "status": "ok",
  "agents": 18,
  "datasources": {"yfinance": "available", "finnhub": "configured"},
  "cache": {"entries": 42, "hit_rate": 0.85},
  "uptime_seconds": 3600.5,
  "version": "7.5.0"
}
```

---

### GET /api/datasources

**Description / 说明:**
List available and configured data sources.

列出可用和已配置的数据源。

**Response / 响应:**
```json
{
  "datasources": [
    {"name": "yfinance", "status": "active", "description": "Yahoo Finance (free)"},
    {"name": "finnhub", "status": "configured", "description": "Finnhub API (requires key)"},
    {"name": "alpha_vantage", "status": "not_configured", "description": "Alpha Vantage (requires key)"}
  ]
}
```

---

### POST /api/cache/clear

**Description / 说明:**
Clear the data cache to force fresh data fetches on next request.

清除数据缓存，下次请求时将重新获取数据。

**Response / 响应:**
```json
{"status": "ok", "message": "Cache cleared"}
```

---

### GET /api/cache/info

**Description / 说明:**
Get cache statistics and status.

获取缓存统计信息。

**Response / 响应:**
```json
{
  "entries": 42,
  "total_size_kb": 256,
  "hit_rate": 0.85,
  "oldest_entry_age_seconds": 1800,
  "ttl_seconds": 3600
}
```

---

## Authentication / 认证

Two optional auth modes can be enabled independently or together:

| Mode | Env var | Credential |
|------|---------|------------|
| API token | `AUGUR_API_TOKEN=your_secret` | Static Bearer token |
| Multi-user JWT | `AUGUR_MULTI_USER=1` | JWT from `POST /api/auth/login` |

When either mode is active, all `/api/*` endpoints require `Authorization: Bearer <token>` except:
- `GET /api/auth/config`
- `GET /api/auth/verify`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /health`, `GET /api/health`

Either credential satisfies auth when both modes are enabled.

**Dashboard:** save the token under Settings → API Token (`localStorage.augur_api_token`) or sign in at `/login` (`localStorage.augur-token`). All `fetch('/api/...')` calls and `/ws/prices` auto-attach the credential.

**CLI (`augur api`):** the lightweight REST server in `src/augur/api.py` honors the same env vars; pass `-H "Authorization: Bearer $AUGUR_API_TOKEN"` to `curl`.

**MCP (`augur mcp-server`):** stdio tools run locally and do **not** read `AUGUR_API_TOKEN`. Missing `FINNHUB_API_KEY` / `ALPHAVANTAGE_API_KEY` only affects optional premium data — yfinance remains the default.

### GET /api/auth/config

Public endpoint (no auth). Tells clients whether credentials are required.

**Response / 响应:**
```json
{"status": "ok", "auth_required": true, "multi_user": false, "api_token": true, "modes": ["token"]}
```

### GET /api/auth/verify

Verify the current Bearer token (API token or JWT).

**Response / 响应:**
```json
{"status": "ok", "authenticated": true, "mode": "token"}
```
`mode` is one of: `open`, `token`, `jwt`.

### GET /api/auth/me

Return the authenticated user (requires `AUGUR_MULTI_USER=1` and a valid JWT).

**Response / 响应:**
```json
{"status": "ok", "user_id": 1, "username": "alice"}
```

### POST /api/auth/login

**Request / 请求:**
```json
{"username": "alice", "password": "secret123"}
```

**Response / 响应:**
```json
{"status": "ok", "token": "<jwt>", "username": "alice"}
```

Login and register are rate-limited to **10 attempts per minute per IP**.

---

## WebSocket / 实时推送

WebSocket endpoints bypass HTTP middleware and enforce the same auth rules separately.

| Endpoint | Description |
|----------|-------------|
| `/ws/prices` | Real-time price tape |
| `/ws/analyze/{ticker}` | Streaming analysis progress |

### WebSocket authentication

When `AUGUR_API_TOKEN` or `AUGUR_MULTI_USER=1` is set, pass the token using either:

1. **Authorization header** (recommended for server-side clients):
   ```
   Authorization: Bearer <token>
   ```

2. **Query parameter** (required for browser `WebSocket` API, which cannot set headers):
   ```
   ws://localhost:8000/ws/prices?token=<token>
   ws://localhost:8000/ws/analyze/AAPL?token=<token>
   ```

JavaScript example:
```javascript
var token = localStorage.getItem('augur_api_token') || localStorage.getItem('augur-token');
var ws = new WebSocket('ws://localhost:8000/ws/prices?token=' + encodeURIComponent(token));
```

Unauthorized connections are closed with WebSocket code `1008`.

---

## Rate Limiting / 限流

All `/api/*` endpoints are subject to IP-based rate limiting:
- **Limit**: 60 requests per minute per IP
- **Header**: `X-RateLimit-Remaining` indicates remaining quota
- **429 Response**: When limit exceeded

Per-ticker analyze endpoints also enforce **30 requests per minute per ticker** (`GET /api/analyze/{ticker}`, etc.).

Auth endpoints (`/api/auth/login`, `/api/auth/register`) are limited to **10 attempts per minute per IP**.

所有 API 接口均受 IP 级别限流保护:
- **限制**: 每 IP 每分钟最多 60 次请求
- **响应头**: `X-RateLimit-Remaining` 显示剩余配额
- **429 响应**: 超出限制时返回

---

## CORS / 跨域

CORS is enabled by default (allow all origins). Configure allowed origins via environment variable:

默认允许所有来源的跨域请求。可通过环境变量配置允许的来源:

```bash
export AUGUR_CORS_ORIGINS="https://myapp.com,https://dashboard.myapp.com"
```

---

## Error Format / 错误格式

All error responses follow a consistent format:

所有错误响应使用统一格式:

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 404
}
```

Common status codes / 常见状态码:
- `400` - Bad Request (invalid ticker format, missing parameters)
- `404` - Not Found (ticker/agent not found)
- `422` - Validation Error (invalid request body)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
