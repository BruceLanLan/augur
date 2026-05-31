# Augur API Reference / API 参考文档

> Version: v7.5.0

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

## Rate Limiting / 限流

All API endpoints are subject to IP-based rate limiting:
- **Limit**: 30 requests per minute per IP
- **Header**: `X-RateLimit-Remaining` indicates remaining quota
- **429 Response**: When limit exceeded

所有 API 接口均受 IP 级别限流保护:
- **限制**: 每 IP 每分钟最多 30 次请求
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
