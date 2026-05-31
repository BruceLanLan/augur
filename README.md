[English](README_EN.md) | 中文

<div align="center">

<img src="docs/images/hero-banner-baoyu.svg" alt="Augur" width="100%"/>

# 🦉 Augur

**你的 AI 投资决策委员会**

*18位投资大师，同时分析，一次共识*

[![v7.8.0](https://img.shields.io/badge/v7.8.0-Latest-00d4aa?style=for-the-badge)](https://github.com/BruceLanLan/augur)
[![18 Masters](https://img.shields.io/badge/18-Investment%20Masters-brightgreen?style=for-the-badge)](#18位投资大师)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude%20%2F%20Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

> **巴菲特会买这只股吗？达利欧怎么看宏观风险？段永平觉得管理层够不够「本分」？**
>
> 别再一个维度猜了。Augur 让 **18位** 顶级投资人同时为你分析，每人给出独立评分，最终汇成一个带 Kelly 仓位建议的加权共识信号。

---

## 🆕 v7.8.0 新功能

| 功能 | 说明 |
|------|------|
| 📊 Bloomberg 仪表盘增强 | SVG 恐慌贪婪仪表盘、Market Pulse 脉搏条、国际市场面板、板块热力图 mini-bar |
| 🎭 自定义 Persona CRUD | 列出/编辑/删除自定义投资人，紫色 CUSTOM 徽章 |
| 🔐 API Token 认证 | AUGUR_API_TOKEN 环境变量，Bearer Token 中间件，Settings 配置面板 |
| 🎨 UI 打磨 | 全面板空状态优雅处理、JS 错误处理增强、CSS 一致性、480px 移动端断点 |
| 📖 集成指南 | MCP/REST/Python SDK/Hermes/OpenClaw 单投资人接入完整文档 |
| 🐳 Docker 完善 | docker-compose.yml 传递 Token，.env.example 补充说明 |

---

## 📋 功能一览 (Feature List)

> Augur 是一个功能完整的多智能体投资分析平台，以下为所有核心功能模块：

| 模块 | 功能 | 说明 |
|------|------|------|
| 🧠 多智能体共识 | 18 Masters Consensus | 18 位投资大师独立分析，加权共识信号 + Kelly 仓位 |
| 📡 自动数据获取 | Auto Data Fetch | yfinance / Finnhub / Alpha Vantage / Stooq 多源 |
| 🔥 板块热力图 | Sector Heatmap | 11 个板块 ETF 涨跌幅可视化 |
| 😱 恐慌贪婪指标 | Fear & Greed Gauge | VIX 驱动 SVG 半圆仪表盘 |
| 🌏 国际市场 | International Markets | 亚太 (HSI, Nikkei, CSI300) + 欧洲 (FTSE, DAX) |
| 📋 自选股 | Watchlist | 添加/删除，localStorage 持久化，批量分析 |
| 🔍 市场扫描器 | Scanner | 预设标的批量评分 heatmap |
| 📈 回测 | Backtest | IC 排行榜 + 命中率评估 |
| 💼 持仓管理 | Portfolio | 持仓追踪、实时盈亏、资产配置图 |
| 🎭 自定义人格 | Custom Persona | 无代码 YAML 创建、CRUD 管理 |
| 🔐 API Token | Auth | 环境变量配置，Bearer 中间件认证 |
| 🤖 多平台 Bot | Telegram/Slack/WeChat/Lark | 通知推送 + 告警阈值 |
| 🔌 MCP 集成 | Claude / Hermes | MCP Server 协议，单/全投资人调用 |
| 🐳 Docker 部署 | Docker Compose | 一键部署，环境变量配置 |
| 💻 CLI | Command Line | augur analyze / consensus / report / inject-soul |
| ⏰ Cron 调度 | Scheduler | 定时监控自选股，阈值触发通知 |
| 📄 深度报告 | Reports | Markdown/HTML 下载，专业可视化 |
| 📡 多数据源 | Multi-Source | yfinance + Finnhub + Alpha Vantage + Stooq 优先级链 |
| 🌐 国际化 | i18n | 中英文切换，localStorage 持久化 |

---

## 🆕 v7.7.0 新功能

| 功能 | 说明 |
|------|------|
| 💼 持仓管理 Portfolio | /portfolio 页面，持仓追踪、实时盈亏、资产饼图、7日价值曲线、一键 Augur 分析 |
| 🎭 人格深度交互 | 向单个大师提问 (Ask Question)、两位大师并排对比 (Compare Two Masters) |
| 🔔 定时监控优化 | 阈值过滤修复、定时任务配置 UI、GET/PUT /api/cron/config、POST /api/cron/run-now |
| 📊 首页数据增强 | 板块热力图、涨跌幅排行、Market Breadth、Consensus Leaderboard、国际指数 |
| 📄 专业报告 | /report/{ticker} 独立全页视图、评分仪表盘、下载 MD/HTML、复制剪贴板、投票表格 |
| 🎨 UI 打磨 | 全局表格排序、活跃导航高亮、Bloomberg 暗色主题全覆盖 |

---

## 🆕 v7.6.0 新功能

| 功能 | 说明 |
|------|------|
| 📋 自选股 Watchlist | 添加/删除自选股，localStorage 持久化，一键批量分析 |
| 📈 迷你走势图 Sparkline | 7 日收盘价 SVG polyline，上涨绿/下跌红，首页 + 自选股 |
| 📊 历史对比 | 同一标的不同时间分析结果对比表格，追踪预测变化 |
| 📦 报告导出增强 | JSON 结构化导出 + CSV 大师评分导出（纯前端 Blob） |
| 🔍 SEO & Open Graph | og:title/description/image + Twitter Card + robots.txt + sitemap.xml |
| 🏷️ 代码质量 | data.py 全量 type hints + docstrings，app.py OpenAPI summary，py.typed |

---

## 🆕 v7.5.0 新功能

| 功能 | 说明 |
|------|------|
| 🌐 i18n 国际化 | 中英文切换，侧边栏一键切换语言，localStorage 持久化 |
| 🔍 Scanner 市场扫描器 | 批量评分 heatmap，预设标的列表，18 位大师并行评分 |
| 🔒 安全加固 | IP 限流 (30/min) / CORS 中间件 / 输入脱敏 / API Key 掩码 |
| ⚡ 性能优化 | ETag + 304 条件请求 / ThreadPoolExecutor 并发数据获取 |
| 🔔 通知系统 | Telegram / Slack / 飞书 / 微信测试通知 + 告警阈值配置 |
| 📄 报告下载 | Markdown 一键导出，复制到剪贴板 |
| 🤖 单 Agent 集成指南 | MCP / REST / Python SDK 接入单个投资人 Agent (详见 [docs/single-persona-integration.md](docs/single-persona-integration.md)) |

---

## ✨ 真实运行效果

```
$ augur analyze NVDA

Auto-fetching data for NVDA from yfinance...
  Price: 820.00 | PE: 45.0 | ROE: 65.0% | GM: 78.0%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NVDA — 18 Masters Consensus
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Signal:     BULLISH
  Score:      7.6 / 10
  Confidence: 82%
  Kelly Size: 9.2%

  Key Findings:
    • 🛡️ AI reinforcing moat, competitive advantage expanding
    • ⚡ AI revenue rapidly growing, clear AGI commercialisation
    • 🚀 Revenue 122%, S-curve early rapid expansion phase

  BULLISH (11): buffett, fisher, aschenbrenner, cathie_wood, thiel...
  NEUTRAL  (5): dalio, marks, graham, soros, serenity
  BEARISH  (2): arps, munger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🚀 30秒上手

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur

# 创建虚拟环境并升级 pip（解决旧版本兼容问题）
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# 安装 Augur
pip install -e ".[data]"

# 开始使用
augur analyze AAPL         # 一键分析，自动获取实时数据
augur consensus NVDA       # 18位共识 + Kelly仓位
augur report TSLA          # 生成深度分析报告
python3 -m dashboard.app   # 启动 Bloomberg 风格 Dashboard
# → 浏览器打开 http://localhost:8000
```

---

## 📸 Dashboard 预览

> *完整截图待补充 (Coming Soon)*

```
┌─────────────────────────────────────────────────────────────┐
│  🦉 Augur Dashboard                                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AUGUR - 输入股票代码，一键获得18位大师共识         │    │
│  │  [AAPL] [NVDA] [TSLA] [MSFT] [GOOGL] [BTC-USD]    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ S&P 500  │ │ NASDAQ   │ │ VIX      │ │ BTC      │      │
│  │ +0.52%   │ │ +0.81%   │ │ 15.2     │ │ +1.2%    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  恐慌与贪婪指标    │    宏观经济快照                │    │
│  │  VIX: 15.2 偏贪婪  │    黄金 / 原油 / BTC         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  精选投资人: [Buffett] [Graham] [Cathie Wood] [段永平]      │
│  18位大师 × 4大流派 × 实时数据 → 一键共识                   │
└─────────────────────────────────────────────────────────────┘
```

Dashboard 功能亮点：
- 🌐 **全球市场总览** — 实时追踪 S&P 500、纳斯达克、恒生、沪深300、VIX、美债、黄金、原油、BTC
- 🔥 **热门标的** — 10 大科技/加密标的实时价格与涨跌
- 😱 **恐慌贪婪指标** — 基于 VIX 自动判断市场情绪
- 🎴 **投资大师卡片** — 18 位大师按流派分类，一键分析
- 🌗 **深色/浅色主题** — 一键切换，偏好自动记忆
- 📊 **深度报告** — 支持 Markdown/PDF 下载

---

## 💡 为什么是 Augur？

| | 传统单策略 | ChatGPT 问答 | **Augur** |
|--|:--:|:--:|:--:|
| 分析维度 | 1 种 | 随机 | **18 种独立视角** |
| 量化评分 | ✗ | ✗ | **0-10 结构化评分** |
| 中国投资人 | ✗ | 有偏见 | **段永平/张磊/李录/但斌** |
| 实时数据 | 手动输 | 无 | **yfinance 自动** |
| 仓位建议 | ✗ | ✗ | **Kelly 公式** |
| 部署到 Claude/Hermes | ✗ | ✗ | **MCP Server** |

---

## 🧠 18位投资大师

<details>
<summary><strong>经典价值派</strong>（点击展开）</summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🏆 **巴菲特** | 护城河 + 可预测盈利 + FCF | 消费/金融蓝筹 |
| 📐 **格雷厄姆** | 安全边际 PE<15 PB<1.5 | 深度价值股 |
| 🧠 **芒格** | 格栅思维 + 逆向 | 被市场误解的企业 |
| 🔬 **费雪** | Scuttlebutt + 毛利率持续性 | 成长型高质量公司 |

</details>

<details>
<summary><strong>成长与创新</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🚀 **彼得林奇** | PEG < 1.5 + 日常可理解 | GARP 成长股 |
| 💡 **凯西伍德** | Wright定律 + TAM扩张 | AI/基因组/区块链 |
| 🏢 **彼得蒂尔** | 0→1 垄断 + 逆向思考 | 科技平台/深科技 |
| 🤖 **阿申布伦纳** | AGI基础设施 + 算力稀缺 | AI/半导体 |

</details>

<details>
<summary><strong>宏观与周期</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🌐 **达利欧** | 全天候 + 债务周期 | 宏观轮动 |
| 🔄 **索罗斯** | 反射性 + 趋势自我强化 | 趋势交易 |
| 📉 **霍华德马克斯** | 钟摆情绪 + 二阶思考 | 周期底部 |
| 🥇 **ARPS** | 实际利率 + Crypto/黄金 | 通胀对冲 |

</details>

<details>
<summary><strong>🇨🇳 中国投资人（独家）</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🎯 **段永平** | 本分 + 极度集中 | 商业模式清晰的消费科技 |
| 🌏 **张磊（高瓴）** | 结构性长期价值 | 中国成长赛道 |
| 🏔️ **李录（喜马拉雅）** | 深度价值 + 安全边际 | 港股/A股低估值 |
| 🫖 **但斌（东方港湾）** | 品牌护城河 + 时代Beta | 消费龙头 |
| ₿ **大宇（BTCdayu）** | 信息差 + 情绪动量 | Crypto/加密赛道 |

</details>

<details>
<summary><strong>前沿特殊策略</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🔭 **Serenity** | AI/半导体供应链瓶颈 | 卡脖子环节标的 |

</details>

---

## 📊 Dashboard

```bash
python3 -m dashboard.app --port 8000 --cors
```

Bloomberg Terminal 风格，**9个页面**，完整分析流程：

| 页面 | 功能 | 亮点 |
|------|------|------|
| **首页** | 快速分析 + 数据源状态 + 热门标的 | 键盘 `/` 快速聚焦，响应式移动布局 |
| **股票分析** | 18位共识 + 可视化报告 | 评分卡片网格 + 多空辩论 + 风险矩阵 |
| **人格系统** | 18位大师卡片 + 搜索/过滤 | 展开看评分权重，Ask Question + Compare |
| **信号监控** | 自选股批量扫描 | 自动 60s 刷新 |
| **持仓管理** | 持仓追踪 + 实时盈亏 + 资产配置图 | /portfolio，localStorage 持久化 |
| **分析报告** | 全页专业报告 + 下载 | /report/{ticker}，MD/HTML 下载 |
| **历史回测** | IC 排行榜 + 命中率 | 评估大师准确率 |
| **设置** | 每位大师独立配置模型 | 实时保存 |
| **创建大师** | 无代码 YAML 自定义 | 即时注册生效 |

**报告下载**：支持 PDF（window.print）和 Markdown 格式下载，方便离线阅读或分享。

<p align="center">
  <img src="docs/images/dashboard-stocks.svg" alt="Stock Analysis Dashboard" width="100%"/>
</p>

---

## 🔌 多平台部署

### Claude Desktop / Hermes (MCP)

```bash
# Step 1: 安装 MCP 支持 (需要 Python 3.10+)
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # 验证可启动
```

**Hermes** (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  augur:
    command: /绝对路径/augur/.venv/bin/augur
    args: [mcp-server]

skills:
  external_dirs:
    - /绝对路径/augur/skills    # 启用 /skill augur-buffett 等命令
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "augur": {
      "command": "/绝对路径/augur/.venv/bin/augur",
      "args": ["mcp-server"]
    }
  }
}
```

7个 MCP 工具：`augur_analyze` · `augur_consensus` · `augur_fetch` · `augur_list_personas` · `augur_configure` · `augur_create_persona` · `augur_debate`

> 所有工具均支持**自动实时数据**：不传指标时自动从 yfinance 获取。

### Telegram / Slack / 微信 / 飞书

```bash
# Telegram
pip install -e ".[telegram]"
export TELEGRAM_TOKEN='your-token'
augur telegram

# Slack
pip install -e ".[slack]"
export SLACK_BOT_TOKEN='xoxb-...' SLACK_APP_TOKEN='xapp-...'
augur slack

# 个人微信 (GeWeChat)
pip install -e ".[wechat]"
augur wechat --mode personal

# 飞书
pip install -e ".[lark]"
export LARK_APP_ID='...' LARK_APP_SECRET='...'
augur lark
```

### Docker

```bash
docker compose up -d dashboard          # http://localhost:8000
docker compose --profile telegram up -d  # + Telegram Bot
```

---

## ⚙️ 完整 CLI（17 个命令）

```bash
# ── 核心分析 ──────────────────────────────────────────────────────────────────
augur analyze AAPL                            # 自动实时数据，18位同时分析
augur analyze NVDA --persona buffett          # 仅用巴菲特框架
augur analyze TSLA --persona cathie_wood --json  # JSON 输出（脚本集成）
augur consensus AAPL                          # 18位加权共识 + Kelly 仓位建议
augur consensus NVDA --json                   # JSON 输出（含个体结果）
augur list-personas                           # 列出所有 18 位投资人

# ── 数据 ──────────────────────────────────────────────────────────────────────
augur fetch 0700.HK                           # 仅获取实时数据（不分析）
augur fetch AAPL --json                       # JSON 格式输出

# ── 回测与 IC 追踪 ────────────────────────────────────────────────────────────
augur backtest AAPL --days 30 --live         # 用真实 yfinance 历史数据
augur backtest AAPL --demo                   # 用模拟数据（快速演示）
augur ic-report                              # Agent 预测准确率排行榜

# ── 自选股监控 ────────────────────────────────────────────────────────────────
augur watchlist-add AAPL --roe 0.55 --gross-margins 0.46 --sector Technology
augur watchlist-show                         # 查看当前自选股列表
augur cron-run                               # 立即运行一次自选股分析
augur cron-start                             # 启动定时守护（工作日 09:00 AM）

# ── 服务启动 ──────────────────────────────────────────────────────────────────
python3 -m dashboard.app --port 8000 --cors  # Bloomberg Dashboard（含完整 API）
augur api --port 8900                        # 轻量 REST API
augur mcp-server                             # MCP Server (stdio, 需 Python 3.10+)

# ── Hermes / Claude 集成 ──────────────────────────────────────────────────────
augur inject-soul --persona buffett -f hermes --profile my-buffett
# → 生成 soul.md 并存入 --output-dir（默认当前目录）

# ── 平台 Bot（需先安装对应 extra） ────────────────────────────────────────────
augur telegram    # pip install -e ".[telegram]" && export TELEGRAM_TOKEN=...
augur slack       # pip install -e ".[slack]" && export SLACK_BOT_TOKEN=... SLACK_APP_TOKEN=...
augur wechat      # pip install -e ".[wechat]"  （个人微信 GeWeChat 模式）
augur wechat --mode wecom    # 企业微信
augur lark        # pip install -e ".[lark]" && export LARK_APP_ID=... LARK_APP_SECRET=...
```

**参数约定（所有命令统一）：**

| 参数类型 | 单位 | 正确示例 | 错误示例 |
|---------|------|---------|---------|
| 利润率 / 增速 / 比率 | 小数（0-1） | `--roe 0.55`（55%） | ~~`--roe 55`~~ |
| 资产负债率 | 小数（0-1） | `--debt-ratio 0.35`（35%） | ~~`--debt-ratio 35`~~ |
| 持仓比例 | 整数百分比 | `--institutional-ownership 66`（66%） | ~~`--institutional-ownership 0.66`~~ |
| 市值 / FCF | **十亿 USD** | `--market-cap 2800`（$2.8T）`--fcf 90`（$90B） | ~~`--market-cap 2800000000000`~~ |

---

## 🏗️ 架构

```
augur/
├── src/augur/
│   ├── personas/           # 18位投资人 Python 引擎
│   │   ├── buffett.py … serenity.py   # 每位独立评分逻辑
│   │   └── base.py         # BaseAgent / MarketContext / AgentResponse
│   ├── coordinator.py      # DecisionCoordinator — 6层加权共识
│   ├── registry.py         # AgentRegistry + half-Kelly 仓位计算
│   ├── data.py             # yfinance 实时数据（自动单位换算）
│   ├── mcp_server.py       # MCP Server (7工具, stdio)
│   ├── cli.py              # Click CLI (20命令)
│   ├── api.py              # 轻量 REST API (FastAPI)
│   ├── backtest.py         # IC 回测框架 + leaderboard
│   ├── cron.py             # 定时分析 + watchlist 管理
│   ├── config.py           # 配置管理（线程安全 RLock）
│   ├── soul.py             # Hermes/Claude soul 注入
│   └── bots/               # Telegram / Slack / WeChat / Lark
├── dashboard/              # Bloomberg 风格 Web UI
│   ├── app.py              # FastAPI + 25+ API 路由
│   └── templates/          # 7个页面（含 create-persona / backtest）
├── skills/                 # Hermes/Claude Skill 定义
│   └── buffett/SKILL.md    # 每位大师独立 Skill
├── personas/               # 深度人格文档 + YAML 自定义
├── config/agents.yaml      # Agent 模型配置
├── Dockerfile + docker-compose.yml
└── pyproject.toml          # 包配置 (augur-agents)
```

**共识引擎 6 层加权：**

```
输入指标 → [18位大师独立分析]
         → 行业感知权重    # 科技股 ↑ Wood/Aschenbrenner
         → 市场机制路由    # 熊市 ↑ Marks/Dalio
         → 滚动 IC 权重   # 历史准确率高者动态加权
         → 多样性惩罚     # 观点相似者减少冗余
         → Kelly 仓位     # 置信度 × 信号强度 → 仓位 %
         → 风险否决层     # 高负债+熊市可否决看多
         → 最终共识信号 + 仓位建议
```

---

## 🔧 YAML 自定义大师

无需写 Python，YAML 文件即可创建自定义投资策略：

```yaml
# personas/custom/my_quant.yaml
agent_id: my_quant
name: "我的量化策略"
philosophy: ["动量", "价值", "低波动"]
scoring_weights:
  momentum: 0.40
  value:    0.35
  safety:   0.25
factors:
  momentum:
    base: 5
    rules:
      - {if: "rsi > 55 and rsi < 75", add: 2}
      - {if: "macd > macd_signal",     add: 1}
      - {if: "price > sma50",          add: 1}
  value:
    base: 5
    rules:
      - {if: "pe > 0 and pe < 15",     add: 3}
      - {if: "pb < 1.5 and pb > 0",   add: 2}
  safety:
    base: 5
    rules:
      - {if: "debt_ratio < 0.3",       add: 2}
      - {if: "current_ratio > 2",      add: 2}
```

保存后立即生效，`augur list-personas` 可见。

---

## 📡 Dashboard API 端点

Dashboard 启动后（`python3 -m dashboard.app --port 8000`）自动提供以下 API：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analyze/{ticker}` | GET | 18位共识分析，无指标时自动 yfinance |
| `/api/fetch/{ticker}` | GET | 仅获取实时行情，不分析 |
| `/api/personas` | GET | 列出所有 18 位投资人 |
| `/api/persona/{id}` | GET | 单投资人详情 |
| `/api/config` | GET/PUT | 全局配置读写 |
| `/api/config/persona/{id}` | GET/PUT | 单投资人模型配置 |
| `/api/models` | GET | 可用模型列表 |
| `/api/watchlist` | GET | 自选股列表 |
| `/api/watchlist/add` | POST | 添加自选股 |
| `/api/watchlist/{ticker}` | DELETE | 移除自选股 |
| `/api/watchlist/run` | POST | 批量分析自选股，保存历史信号 |
| `/api/custom-persona` | POST | 创建 YAML 自定义投资人（热加载）|
| `/api/backtest/run` | GET | 运行 IC 历史回测 |
| `/api/backtest/leaderboard` | GET | IC 排行榜 |
| `/api/search` | GET | 股票代码搜索 |
| `/health` | GET | 健康检查 |

---

## ❓ 常见问题

<details>
<summary>augur analyze 报错 "yfinance not installed"</summary>

```bash
pip install -e ".[data]"
```
</details>

<details>
<summary>MCP Server 报错 "No module named mcp"</summary>

mcp 包需要 Python 3.10+：
```bash
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # 验证可启动
# 然后在 ~/.hermes/config.yaml 中用绝对路径注册
```
</details>

<details>
<summary>分析结果总是 NEUTRAL，评分偏低</summary>

检查参数单位是否正确（这是最常见的错误）：
- ✅ `--roe 0.55`（55%）  ❌ ~~`--roe 55`~~
- ✅ `--debt-ratio 0.35`（35%）  ❌ ~~`--debt-ratio 35`~~
- ✅ `--market-cap 2800`（$2.8T）  ❌ ~~`--market-cap 2800000000000`~~
- ✅ `--gross-margins 0.46`（46%）  ❌ ~~`--gross-margins 46`~~
</details>

<details>
<summary>Dashboard 页面不显示或 "加载中" 卡住</summary>

```bash
# 1. 检查服务是否正常
curl http://localhost:8000/health   # 应返回 {"status":"ok","agents":18}

# 2. 确认 yfinance 已安装（自动数据获取）
pip install -e ".[data]"

# 3. 启用 CORS（供前端调用）
python3 -m dashboard.app --port 8000 --cors
```
</details>

<details>
<summary>Telegram Bot 发 /analyze AAPL 返回 NEUTRAL（全零数据）</summary>

需要安装 yfinance：
```bash
pip install -e ".[data,telegram]"
# Bot 在无指标时会自动从 yfinance 获取实时数据
```
</details>

<details>
<summary>Kelly 仓位建议显示 0% 或 N/A</summary>

Kelly 只在 BULLISH 信号且 score > 5 时给出非零建议。NEUTRAL/BEARISH 信号下，Kelly 保守返回 0。
</details>

<details>
<summary>pip install 报错 "File 'setup.py' not found"</summary>

这是因为系统 pip 版本太旧，不支持 pyproject.toml 格式。解决方法：

```bash
# 方法1：使用虚拟环境（推荐）
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[data]"

# 方法2：直接升级系统 pip
python3 -m pip install --upgrade pip setuptools wheel
pip install -e ".[data]"
```

注意：macOS 自带的 pip 通常较旧（pip < 21），升级后即可正常识别 pyproject.toml。
</details>

<details>
<summary>自定义 YAML Persona 创建后不出现</summary>

Dashboard 已支持热加载（保存 YAML 后同一进程立即可用）。CLI/API 重启后自动加载 `personas/custom/*.yaml`。
</details>

---

## 🤝 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)，包含：新增投资人（YAML/Python）、修复 Bug、Dashboard 开发、Bot 开发、参数约定等完整指南。

- **新投资人** → `personas/custom/` 放 YAML，或仿 `src/augur/personas/buffett.py` 写 Python
- **算法优化** → 改进 `src/augur/coordinator.py` 共识机制
- **新平台 Bot** → 在 `src/augur/bots/` 添加，参考 `telegram_bot.py`
- **Web UI** → 完善 `dashboard/`，CSS 变量见 `bloomberg.css`

---

## 📋 Changelog

### v7.3.1 — Dashboard 数据密度 & 报告深化

- 首页新增热门标的实时行情面板（10 大 Tickers）、恐慌与贪婪指标、宏观经济快照
- 报告可视化增强：投资风格标签、关键财务指标面板、打印优化、复制报告链接
- 所有页面 `<title>` 统一规范化，版本号升级至 v7.3.1
- 新增 `/api/hot-tickers` 端点

### v7.3.0

Dashboard 全面增强 + 报告可视化升级 + 多数据源链路 + 文档完善（公开发布版）。

#### Dashboard 增强
- 数据源状态面板：实时显示 yfinance/Finnhub/Alpha Vantage/Stooq 各数据源连接状态
- 快速分析热门标的：首页预置 GOOGL / BTC-USD / 00700.HK / BABA 一键分析
- 响应式移动布局：全面适配手机端浏览，窄屏自动调整卡片与表格

#### 报告可视化
- 18 位大师可视化评分卡片网格：每位大师独立评分卡，一目了然
- 多空辩论双栏布局：Bull vs Bear 观点对照展示
- 风险矩阵卡片：结构化风险因子可视化
- 执行摘要头部卡片：核心结论高亮展示
- PDF 下载（window.print 优化打印样式）
- Markdown 下载：一键导出完整分析报告

#### 多数据源
- yfinance（主数据源）+ Finnhub（可选）+ Alpha Vantage（可选）+ Stooq（兜底）
- 数据源自动降级链路：主源失败时自动切换备选源，确保数据可用

#### 文档
- 双语 README（中文/英文）同步更新
- 新增 [单个投资人接入指南](docs/single-persona-integration.md)：Hermes / Open Claw / Claude Desktop 三种接入方式
- 新增 [数据源说明文档](docs/data-sources.md)

---

### v7.2.0

深度报告专业化 + 多数据源 + 关键交互修复（发布前质量加固）。

#### 深度分析报告（专业多大师融合研报）
- 报告全面重写：执行摘要改为中性的「投资委员会综合裁决」，**融合全部 18 位大师视角，不再偏向巴菲特单一框架**
- 新增模块：评级卡（A-E 评级 + 共识强度）、一句话裁决、18 位大师评分总表（含流派/框架）、**分流派深度分析**（价值/成长/宏观风险/技术量化）、**多空辩论**（最看好 vs 最谨慎 3 位）、**分歧焦点**（最有价值部分：识别最大分歧维度）、共识与风险矩阵、仓位建议
- 财务单位修正：ROE/毛利率/增长率正确显示为百分比，市值/FCF 正确换算（$X.XXB / 万亿）
- 浮点精度与 Markdown 噪声清理；Dashboard 报告改为富 Markdown 渲染（标题/表格/列表）

#### 数据源扩展与数据修复
- 新增 `src/augur/datasources/` 数据源抽象层：**yfinance 优先 → Stooq 兜底 → 空 context**，消除单点故障
- **修复严重数据污染 Bug**：yfinance 返回的 NaN 经 `x or 0` 兜底失效（NaN 为 truthy），会原样灌入所有指标导致 persona 评分错乱——新增 `safe_num()` 统一清洗 None/NaN/inf
- 单位换算与持股比例裁剪修复

#### 交互/UX 修复（解决"点击分析没反应/看不到报告"）
- **修复前端 fetch 未检查 HTTP 状态码**：后端返回错误（限流/非法代码/500）时不再渲染虚假的"HOLD"空结果，而是显示明确错误
- 新增首次使用引导横幅 + 一键示例（AAPL/NVDA/TSLA/MSFT，无需手填指标）
- 加载状态分阶段进度文案 + 超时保护（不再无限转圈）
- 「生成深度分析报告」从隐蔽小按钮提升为醒目主按钮；报告失败有内联错误 + 重试
- 空状态友好引导、窄屏适配、错误信息可操作化

#### 测试
- 测试从 372 增至 448（新增数据源 33、报告增强、前端错误处理等）

---

### v7.1.0

新增深度分析报告功能 + 关键 UI 修复。

#### 新功能
- **深度分析报告 `augur report`**: 一键生成中文 Markdown 深度分析报告（12模块框架），包含执行摘要、Agent 共识表、分主题分析、财务概览、风险矩阵、仓位建议
- **API 端点 `/api/report/{ticker}`**: 支持 GET（自动分析+生成报告）和 POST（复用已有分析数据）
- **Dashboard 集成**: stocks.html 新增"生成深度报告"按钮，支持复制/下载 .md
- 首页"查看完整分析"链接自动触发深度报告生成

#### 关键修复
- **修复 Dashboard 分析结果不显示**: `stocks.html` 中 `resultsEl.style.display` 在隐藏后未恢复为 `block`，导致用户点击分析按钮后看不到任何结果
- 修复协调器权重行业匹配假阳性（子字符串 "ai" 不再匹配 "retail"）
- 修复 API 速率限制内存泄漏（自动清理过期 key）
- 修复 Lynch PEG 除零、Graham PE=0 中性评分
- 修复 Kelly 仓位 1% 最低仓位需要 confidence >= 0.5
- 修复 `load_watchlist()` DEFAULT_CONFIG 浅拷贝污染
- 清理 29 个文件中的未使用 import

#### 测试
- 新增 126 个测试（从 78 增加到 372 个）
- 涵盖深度报告生成、debate 功能、watchlist/cron、IC report

---

### v7.0.0

经过 7 轮代码审查、Bug 修复和性能优化后的重大版本更新。

#### 安全修复（严重）
- **严重**: 将 `persona_loader.py` 中危险的 `eval()` 替换为基于 AST 的沙箱执行，防止恶意 YAML 条件触发任意代码执行
- **严重**: 修复 `soul.py` 中 `inject_soul()` 的路径遍历漏洞，防止写入任意目录
- 修复 Dashboard `signals.html` 中的 XSS 漏洞（内联 onclick 字符串插值）
- 在 API、MCP 和 Dashboard 端点中增加 ticker 正则校验
- 添加全局异常处理器，防止通过 API 响应泄露堆栈信息

#### Bug 修复
- 修复 `data.py` 中 yfinance 返回负 `debt_to_equity` 时的 ZeroDivisionError
- 修复大宇 Persona 动量 elif 链排序错误（分支被遮蔽）
- 修复所有 Agent 返回 ERROR 时 Coordinator 崩溃（total_weight==0）
- 修复 CLI 缺失的 sector/industry 参数未传递给 MarketContext
- 修复 cron 配置浅合并导致丢失嵌套默认值（timezone、notifications）
- 全部 18 个 Persona 文件现在将评分限制在 [0, 10] 范围内
- 为 Munger 和 Dalio Persona 增加了除零保护

#### 性能优化
- DecisionCoordinator 现使用 ThreadPoolExecutor 并行执行 18 个 Agent 分析（最高 8 倍加速）
- 每个 Agent 增加 30 秒超时，防止挂起
- 增加性能计时记录（metadata 中包含 analysis_ms 和 consensus_ms）
- Dashboard 使用 Page Visibility API 在后台标签页暂停轮询

#### 用户体验
- 新增 `--no-color` CLI 选项（同时支持 NO_COLOR 环境变量）
- 改进 CLI 输出格式：对齐表格和边框框
- 所有错误信息现在可操作（包含 pip install 命令、--help 建议）
- 新增 `src/augur/errors.py` 统一错误响应格式
- 新增 `src/augur/optional_deps.py` 可选依赖缺失时优雅降级
- Dashboard 模板全面增加 ARIA 无障碍标签
- Dashboard API 响应现包含统一的 `status` 字段和 ISO 8601 时间戳

#### 基础设施
- Dockerfile：添加非 root 用户 `augur` 提升安全性
- docker-compose.yml：移除已弃用的 `version` 字段，添加健康检查
- requirements.txt：添加缺失的 `httpx>=0.24.0`
- Scanner 模块：添加 6 个缺失的 Agent 导出以保持向后兼容
- Cron：增加 PID 文件并发保护和 SIGTERM 信号处理

#### 测试
- 新增 173 个回归测试（从 78 个增加到 251 个）
- 完整端到端管道测试（CLI + API）
- 数据管道验证测试
- Dashboard 错误处理测试
- 安全攻击向量测试（eval 注入、XSS、路径遍历）
- 性能基线测试

#### 架构
- 新模块：`cli_format.py`、`errors.py`、`optional_deps.py`、`bots/utils.py`
- Bot 共享工具模块消除 ticker 提取代码重复

---

## 📈 Star History

<a href="https://star-history.com/#BruceLanLan/augur&Timeline">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline" />
 </picture>
</a>

---

<div align="center">

MIT License · Built by [BruceLanLan](https://github.com/BruceLanLan)

*📌 仅供学习研究，不构成投资建议*

</div>
