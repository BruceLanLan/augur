[English](README_EN.md) | 中文

<p align="center">
  <img src="https://img.shields.io/badge/v5.5-Latest-blue?style=for-the-badge" alt="v5.5"/>
  <img src="https://img.shields.io/badge/17-Investor%20Personas-brightgreen?style=for-the-badge" alt="17 Personas"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/pip%20install-augur--agents-orange?style=for-the-badge&logo=pypi" alt="pip install"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT"/>
</p>

<h1 align="center">Augur</h1>
<h3 align="center">多智能体投资分析系统 - 17位虚拟投资大师为你决策</h3>

<p align="center">
  <img src="docs/images/hero-banner-baoyu.svg" alt="Augur" width="100%"/>
</p>

<p align="center">
  <em>17位AI投资大师(含5位中国投资人) | 多维度共识分析 | Bloomberg风格仪表盘 | 多平台部署</em>
</p>

---

## 快速开始

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e .
augur analyze AAPL
```

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 17位投资大师人格 | 价值投资到币圈博弈、美股到中国市场，每位大师有独立人格与评分逻辑 |
| 多Agent共识机制 | 行业感知权重 + 市场机制路由 + 滚动IC动态权重 + 多样性惩罚 |
| 实时数据 (yfinance) | 自动获取美股/港股/A股价格、估值、基本面和技术指标 |
| Bloomberg风格 Dashboard | 暗色主题 FastAPI 界面，7个页面完整覆盖分析流程 |
| 历史回测 + IC追踪 | 回放历史数据，追踪每位Agent预测准确率与排行 |
| MCP Server | 6个标准工具，供 Claude Desktop / Hermes 等直接调用 |
| 多平台 Bot | Telegram / Slack / 微信(3模式) / 飞书(2模式) |
| Cron 定时分析 | 自选股监控 + 定时推送到全平台 |
| YAML自定义人格 | 无需写代码，YAML文件即可创建自定义投资策略Agent |

---

## 17位投资大师

| # | 投资人 | Skill | 风格 | 核心指标 | 推荐模型 |
|---|--------|-------|------|---------|---------|
| 1 | Warren Buffett | `augur-buffett` | 护城河价值投资 | 毛利率>40%、ROE>15%、负债<50% | claude-sonnet-4-6 |
| 2 | Benjamin Graham | `augur-graham` | 深度价值/安全边际 | PE<15、PB<1.5、流动比>2 | claude-sonnet-4-6 |
| 3 | Peter Lynch | `augur-lynch` | GARP成长 | PEG<1.5、营收增速>15% | claude-sonnet-4-6 |
| 4 | Ray Dalio | `augur-dalio` | 宏观/全天候 | 四象限分析、债务周期 | claude-sonnet-4-6 |
| 5 | Charlie Munger | `augur-munger` | 格栅理论/多元思维 | ROE>20%、护城河+管理层 | claude-sonnet-4-6 |
| 6 | George Soros | `augur-soros` | 反身性/宏观交易 | 反身性信号、趋势动量 | claude-sonnet-4-6 |
| 7 | Howard Marks | `augur-marks` | 周期/逆向投资 | 周期位置、市场情绪 | claude-sonnet-4-6 |
| 8 | Cathie Wood | `augur-cathie-wood` | 颠覆性创新 | 营收增速>30%、TAM | claude-sonnet-4-6 |
| 9 | Philip Fisher | `augur-fisher` | 成长股/闲聊法 | 研发>10%、毛利率>50% | claude-sonnet-4-6 |
| 10 | ARPS | `augur-arps` | Crypto/黄金宏观 | BTC相关性、黄金避险 | claude-sonnet-4-6 |
| 11 | Leopold Aschenbrenner | `augur-aschenbrenner` | AI地缘政治 | AI投入、算力需求 | claude-opus-4-7 |
| 12 | 大宇 (BTCdayu) | `augur-dayu` | 信息差/情绪动量 | 情绪动量>估值 | deepseek-v4 |
| 13 | Peter Thiel | `augur-thiel` | 从0到1垄断 | 网络效应、技术壁垒 | claude-sonnet-4-6 |
| 14 | 段永平 | `augur-duan-yongping` | 本分/极度集中 | 商业模式清晰、管理层本分 | deepseek-v4 |
| 15 | 张磊 (高瓴) | `augur-zhang-lei` | 长期结构性价值 | 营收增速>15%、结构性赛道 | deepseek-v4 |
| 16 | 李录 (喜马拉雅) | `augur-li-lu` | 深度价值/安全边际 | PE<25、ROE>12%、无高负债 | claude-sonnet-4-6 |
| 17 | 但斌 (东方港湾) | `augur-dan-bin` | 品牌护城河/时代Beta | 毛利率>40%、定价权 | kimi-k2 |

> 每位投资人都有: 完整人格文档(`personas/*.md`) + 独立Skill(`skills/*/SKILL.md`) + Python分析引擎(`src/augur/personas/*.py`)

---

## 人格进化追踪

系统追踪每位大师的持仓变化与风格漂移，分析时自动注入当前状态上下文:

| 投资人 | 关键进化 | 核心漂移 |
|--------|---------|---------|
| Buffett | 1965 伯克希尔 - 1988 可口可乐 - 2016 苹果 - 2026 CRCL | 纯烟蒂 - 护城河成长 - 接受科技 |
| Munger | 1972 See's Candies - 2002 中国 - 2020 比亚迪 | 格雷厄姆式 - 多元思维格栅 |
| Dalio | 1982 押注失误 - 2008 看对次贷 - 2012 全天候 | 纯宏观 - 系统化全天候 |
| 段永平 | 2001 步步高 - 2011 苹果建仓 - 2022 腾讯/网易 | 企业家投资 - 价值集中 |
| 张磊 | 2005 $2000万 - 2012 京东 - 2022 新能源转型 | 中国互联网 - 新能源 |
| 李录 | 2002 比亚迪(20年持有) - 2023 重仓Alphabet | 深度价值 - 全球集中 |
| 但斌 | 2003 茅台 - 2016 崩盘坚守 - 2023 AI消费 | 消费品牌 - AI+消费 |
| 大宇 | 2021 BTC 3000布局 - 2024 MEME - 2026 AI+Crypto | 技术分析 - 叙事动量 |

---

## 使用方式

### CLI 命令 (15+)

```bash
# 核心分析
augur analyze AAPL                    # 单标的分析 (自动获取实时数据)
augur consensus NVDA                  # 17位大师共识
augur list-personas                   # 列出所有投资人
augur fetch 0700.HK --json            # 仅获取市场数据

# 服务启动
augur mcp-server                      # MCP Server (stdio, 供Claude/Hermes调用)
augur api --port 8900                 # REST API 服务

# 人格注入
augur inject-soul --profile my-buffett --persona buffett --format hermes

# 平台 Bot
augur telegram                        # Telegram Bot
augur slack                           # Slack Bot (Socket Mode)
augur slack --mode http --port 3000   # Slack Bot (HTTP Mode)
augur wechat                          # 个人微信 (GeWeChat, 推荐)
augur wechat --mode wecom             # 企业微信
augur wechat --mode webhook           # 微信 Webhook 推送
augur lark                            # 飞书 Event 订阅
augur lark --mode webhook             # 飞书 Webhook 推送

# 定时与监控
augur cron-run                        # 手动运行一次分析
augur cron-start                      # 启动定时守护进程
augur watchlist-add AAPL --pe 32      # 添加自选股
augur watchlist-show                  # 查看自选股

# 回测
augur backtest AAPL --days 60 --live  # 真实历史数据回测
augur ic-report                       # IC 排行榜
augur ic-report --agent buffett       # 特定 Agent IC
```

### REST API

| Endpoint | Method | 说明 |
|----------|--------|------|
| `/api/analyze/{ticker}` | GET | 17位大师共识分析 (支持自动获取) |
| `/api/fetch/{ticker}` | GET | 获取实时市场数据 |
| `/api/search?q=` | GET | 搜索股票代码 |
| `/api/personas` | GET | 获取所有投资人列表 |
| `/api/persona/{agent_id}` | GET | 获取单个投资人详情 |
| `/api/config` | GET/PUT | 完整配置 CRUD |
| `/api/config/persona/{id}` | GET/PUT | 单个投资人模型配置 |
| `/api/models` | GET | 可用模型列表 |
| `/api/custom-persona` | POST | 创建自定义投资人 |
| `/api/schema/persona` | GET | Persona YAML Schema |
| `/api/backtest/run?ticker=X&days=N` | GET | 运行回测 |
| `/api/backtest/leaderboard` | GET | IC 排行榜 |
| `/health` | GET | 健康检查 |

### MCP Server (6 Tools)

| 工具 | 说明 |
|------|------|
| `augur_analyze` | 单投资人分析指定标的 |
| `augur_consensus` | 17位大师共识分析 |
| `augur_list_personas` | 列出所有可用投资人 |
| `augur_configure` | 运行时配置管理 |
| `augur_create_persona` | 创建自定义投资人人格 |
| `augur_debate` | 多Agent辩论模式 |

**Hermes 配置:**
```yaml
mcp_servers:
  augur-agents:
    command: augur
    args: [mcp-server]
```

**Claude Desktop 配置:**
```json
{
  "mcpServers": {
    "augur-agents": {
      "command": "augur",
      "args": ["mcp-server"]
    }
  }
}
```

### Web Dashboard (7 页面)

```bash
python3 -m dashboard.app --port 8000 --cors
```

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `/` | 系统概览 + 快速分析 + 状态 |
| 人格 | `/personas` | 17位大师卡片 + 搜索筛选 |
| 股票分析 | `/stocks` | 深度分析 + 实时评分 + 自动获取 |
| 信号监控 | `/signals` | 自选股批量扫描 |
| 回测 | `/backtest` | 历史回测 + IC排行 |
| 设置 | `/settings` | Agent模型配置 |
| 创建人格 | `/create_persona` | YAML 自定义投资人 |

---

## 实时数据 (yfinance)

自动获取实时市场数据，无需手动输入财务指标。

**支持市场:**

| 市场 | 代码格式 | 示例 | 延迟 |
|------|---------|------|------|
| 美股 (NYSE/NASDAQ) | `TICKER` | AAPL, NVDA | ~15分钟 |
| 港股 (HKEX) | `XXXX.HK` | 0700.HK | ~15分钟 |
| A股-上交所 | `XXXXXX.SS` | 600519.SS | ~15分钟 |
| A股-深交所 | `XXXXXX.SZ` | 000858.SZ | ~15分钟 |

**安装:** `pip install 'augur-agents[data]'`

**获取的指标:** 价格、PE、PB、PS、ROE、毛利率、营业利润率、营收增速、净利润增速、负债比率、自由现金流、市值、流动比率、RSI(14)、MACD(12/26/9)、SMA20/50

**限制:** 数据延迟约15分钟(非实时Level 1)，部分A股/港股字段可能缺失，数据缓存5分钟，依赖 Yahoo Finance 可能存在地区限制。

---

## 平台 Bot

### Telegram

```bash
pip install 'augur-agents[telegram]'
export TELEGRAM_TOKEN='your-bot-token'
augur telegram
```

**命令:** `/analyze AAPL` | `/consensus NVDA` | `/ask buffett 分析AAPL` | `/personas` | `/help`

支持自然语言: `@巴菲特 分析AAPL`

### Slack

```bash
pip install 'augur-agents[slack]'
# Socket Mode (开发)
export SLACK_BOT_TOKEN='xoxb-...' SLACK_APP_TOKEN='xapp-...'
augur slack
# HTTP Mode (生产)
export SLACK_BOT_TOKEN='xoxb-...' SLACK_SIGNING_SECRET='...'
augur slack --mode http --port 3000
```

**命令:** `/augur-analyze AAPL` | `/augur-ask buffett analyze AAPL` | `/augur-personas`

频道中 `@augur analyze AAPL` 也可触发。使用 Block Kit 富文本输出。

### 微信 (3种模式)

```bash
pip install 'augur-agents[wechat]'

# 模式一: 个人微信 (推荐, GeWeChat 扫码即用)
export GEWECHAT_TOKEN='...' GEWECHAT_BASE_URL='http://127.0.0.1:2531/v2/api'
augur wechat --mode personal --port 8066

# 模式二: 企业微信
export WECHAT_CORP_ID='...' WECHAT_CORP_SECRET='...' WECHAT_AGENT_ID='...'
export WECHAT_TOKEN='...' WECHAT_AES_KEY='...'
augur wechat --mode wecom --port 8080

# 模式三: Webhook (仅推送, 配合 Cron)
export WECHAT_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx'
augur wechat --mode webhook
```

个人微信需先启动 GeWeChat Docker:
```bash
docker compose --profile wechat up -d gewe
```

**命令:** 直接输入代码如 `AAPL` | `分析 NVDA pe=45` | `@段永平 TSLA` | `投资人列表`

### 飞书 (2种模式)

```bash
pip install 'augur-agents[lark]'

# Event 订阅模式 (接收+发送)
export LARK_APP_ID='...' LARK_APP_SECRET='...'
export LARK_VERIFICATION_TOKEN='...' LARK_ENCRYPT_KEY='...'
augur lark --mode event --port 9000

# Webhook 模式 (仅推送)
export LARK_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'
augur lark --mode webhook
```

**命令:** `分析 AAPL pe=32` | `@张磊 PDD` | `投资人列表`

使用交互式卡片消息输出(信号颜色 + 评分 + Agent明细)。

---

## Cron 定时分析 + Watchlist

```bash
augur watchlist-add AAPL --pe 32 --roe 0.55
augur watchlist-show
augur cron-run         # 手动触发一次
augur cron-start       # 启动定时守护
```

**配置文件** (`~/.augur/watchlist.yaml`):
```yaml
watchlist:
  - ticker: AAPL
    pe: 32
    roe: 0.55
schedule:
  cron: "0 9 * * 1-5"
  timezone: "Asia/Shanghai"
notifications:
  telegram: { enabled: true, chat_id: "...", token: "..." }
  slack: { enabled: true, channel: "#signals", token: "xoxb-..." }
  wechat: { enabled: true, webhook_url: "https://..." }
  lark: { enabled: true, webhook_url: "https://..." }
  alert_threshold: 3
```

---

## Docker 部署

```bash
# Dashboard + API
docker compose up -d dashboard        # http://localhost:8000

# Telegram Bot
export TELEGRAM_TOKEN=your_token
docker compose --profile telegram up -d

# 全部服务
docker compose --profile full --profile telegram --profile cron up -d

# Makefile 快捷命令
make docker-build && make docker-up
```

---

## 项目架构

<p align="center">
  <img src="docs/images/architecture-baoyu.svg" alt="Augur Architecture" width="100%"/>
</p>

```
augur/
├── src/augur/                  # pip 包主模块
│   ├── cli.py                  # Click CLI (15+ commands)
│   ├── mcp_server.py           # MCP Server (6 tools, stdio)
│   ├── api.py                  # REST API (FastAPI)
│   ├── registry.py             # AgentRegistry + DecisionCoordinator
│   ├── data.py                 # 实时数据 (yfinance)
│   ├── backtest.py             # 历史回测 + IC
│   ├── cron.py                 # 定时分析 + Watchlist
│   ├── bots/                   # 多平台 Bot
│   │   ├── telegram_bot.py
│   │   ├── slack_bot.py
│   │   ├── wechat_bot.py
│   │   └── lark_bot.py
│   └── personas/               # 17位投资人 Agent
│       ├── base.py             # 基类 + MarketContext + AgentResponse
│       ├── buffett.py ... dan_bin.py
│       └── (17个 Python 模块)
├── scanner/                    # 向后兼容 shim
├── dashboard/                  # Bloomberg风格 Web UI
│   ├── app.py                  # FastAPI + 路由
│   └── templates/              # 7个页面模板
├── skills/                     # 独立 Skill (agentskills.io)
├── personas/                   # 投资人深度文档 + custom/ YAML
├── config/agents.yaml          # Agent LLM 模型配置
├── pyproject.toml              # pip 包配置 (augur-agents)
├── Dockerfile                  # 容器化
└── docker-compose.yml          # 多服务编排
```

**共识机制:**

<p align="center">
  <img src="docs/images/consensus-flow.svg" alt="Consensus Flow" width="100%"/>
</p>

17位Agent独立分析，通过6层加权汇总:
1. 行业感知权重 - 科技股给 Wood/Aschenbrenner 更高权重
2. 市场机制路由 - 熊市时 Marks/Dalio 权重提升
3. 滚动IC权重 - 历史准确率高的Agent动态加权
4. 多样性惩罚 - 观点相似的Agent减少冗余权重
5. Kelly仓位建议 - 基于共识和置信度给出仓位比例
6. 风险否决层 - 高负债+熊市时可否决共识看多

---

## 版本日志

| 版本 | 内容 |
|------|------|
| **v5.5** | 文档重构 + pyproject.toml 元数据完善 |
| **v5.4** | 实时行情接入 (yfinance) - 自动获取美股/港股/A股数据 |
| **v5.3** | 个人微信接入 (GeWeChat) - 扫码即用, 三模式支持 |
| **v5.2** | UX打磨 - 键盘快捷键 + 骨架屏 + Score仪表 + 移动端 |
| **v5.1** | 历史回测系统 + Agent IC追踪 + 排行榜 |
| **v5.0** | Docker容器化 + docker-compose多服务编排 |
| **v4.6** | 微信(企业微信+Webhook) + 飞书(Event+Webhook) |
| **v4.5** | 信号监控页 + 自定义投资人UI + Watchlist API |
| **v4.4** | Bloomberg Terminal风格UI + Hermes侧边栏 |
| **v4.3** | Slack Bot (Socket+HTTP) + Cron推送 |
| **v4.2** | Telegram Bot + Cron定时分析 + Watchlist |
| **v4.1** | Config REST API + Dashboard UI/UX优化 |
| **v4.0** | pip包化 + CLI + MCP Server + Soul Injector |
| **v3.5** | Baoyu漫画风格配图 + 17投资人头像 |
| **v3.4** | Skill封装 + 模型配置 |
| **v3.3** | FastAPI Dashboard (5页路由) |
| **v3.2** | 4位中国投资人加入 (17位) |
| **v3.0** | 正式更名Augur + 共识引擎 |
| **v2.0** | 13位投资人人格系统 |
| **v1.0** | 巴菲特单人格分析 |

---

## 为什么叫 Augur?

> **Augur (奥格)** - 拉丁语，古罗马的占卜官。Augur 专门负责解读征兆、预测未来 - 从鸟群的轨迹、闪电的方向中看见即将到来的变化。这正是这个系统要做的事: 让17位投资大师帮你在市场变化之前看见先机。

| 神祇 | 角色 | 象征 |
|------|------|------|
| **Hermes** (赫尔墨斯) | 神的信使，传递信息 | 信息传递、沟通 |
| **Augur** (奥格) | 解读征兆，预测未来 | 分析解读、先见之明 |

Hermes 负责传递信息，Augur 负责解读信息。一个传信，一个预测，天然互补。

---

## 贡献

1. **新投资人** - `personas/custom/` 添加 YAML，或参考 `src/augur/personas/buffett.py` 写 Python Agent
2. **新 Skill** - 参考 `skills/buffett/SKILL.md` 格式创建独立 Skill
3. **算法优化** - 改进评分逻辑或共识机制
4. **Bot 适配** - 在 `src/augur/bots/` 添加新平台
5. **Web UI** - 完善 `dashboard/` 前端

---

## Star History

<a href="https://www.star-history.com/?repos=BruceLanLan%2Faugur&type=timeline&logscale=&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=BruceLanLan/augur&type=timeline&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=BruceLanLan/augur&type=timeline&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=BruceLanLan/augur&type=timeline&legend=top-left" />
 </picture>
</a>

---

## License

MIT License - 详见 [LICENSE](LICENSE)

<p align="center">
  <sub>Built with care by <a href="https://github.com/BruceLanLan">BruceLanLan</a></sub>
</p>
