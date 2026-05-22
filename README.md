<p align="center">
  <img src="https://img.shields.io/badge/17-Investor%20Personas-brightgreen?style=for-the-badge" alt="17 Personas"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-Web%20UI-teal?style=for-the-badge&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Skill-Ready-purple?style=for-the-badge" alt="Skill Ready"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT"/>
</p>

<h1 align="center">🦉 Augur</h1>
<h3 align="center">多智能体投资分析系统 — 17位虚拟投资大师为你决策</h3>

<p align="center">
  <img src="docs/images/hero-banner-baoyu.svg" alt="Augur" width="100%"/>
</p>

<p align="center">
  <em>17位AI投资大师（含5位中国投资人）· 多维度共识分析 · Bloomberg风格仪表盘 · 可部署到任意平台</em>
</p>

<p align="center">
  <a href="#-核心功能">功能</a> ·
  <a href="#-为什么叫-augur">命名由来</a> ·
  <a href="#-17位投资大师">投资人</a> ·
  <a href="#-快速开始">开始使用</a> ·
  <a href="#-web-dashboard">Web界面</a> ·
  <a href="#-整合到任意平台">平台整合</a> ·
  <a href="#-项目架构">架构</a> ·
  <a href="#-路线图">路线图</a>
</p>

> **Warren Buffett (沃伦·巴菲特)** 会买这只股票吗？**Ray Dalio (瑞·达利欧)** 怎么看当前宏观周期？**段永平** 这家公司的管理层"本分"吗？
>
> 不用猜。Augur 用 **17位**虚拟投资大师的独立 Agent（含段永平、张磊、李录、但斌等中国顶级投资人），对同一标的给出各自的评分、信号和理由，再用多 Agent 共识机制汇总，给你一份「投资大师天团」的集体判断。**每位大师都是一个独立的 Skill，可以单独部署到 Claude、Hermes、Telegram、Slack、微信等任意平台。**

---

## ⚡ 核心功能

| 功能 | 说明 |
|------|------|
| 🧠 **17位投资大师人格** | 从价值投资到币圈博弈、从美股到中国市场，每位大师都有独立的人格、灵魂和评分逻辑 |
| 🔌 **独立 Skill 封装** | 每位投资人都是一个独立 Skill，可单独安装到 Hermes/Claude/OpenClaw/Telegram 等任意平台 |
| 🤖 **可配置 LLM 模型** | 每位 Agent 可指定不同模型：DeepSeek/Kimi/Claude/GPT-4o/Minimax，灵活适配 |
| 🔄 **多Agent共识机制** | 行业感知权重 + 市场机制路由 + 滚动IC动态权重 + 多样性相关性惩罚 |
| 📈 **人格进化追踪** | 追踪每位大师的持仓变化与风格漂移，动态注入分析上下文 |
| 🌐 **跨资产覆盖** | 美股/港股/A股/Crypto — 一个系统通吃 |
| 📊 **Web Dashboard** | Bloomberg暗色风格FastAPI界面，实时呈现分析结果 |
| 🎨 **YAML自定义人格** | 无需写代码，YAML文件即可创建你自己的投资策略Agent |
| 📋 **一键共识报告** | 所有Agent分析完成后自动汇总共识评级、分歧点与Kelly仓位建议 |

---

## 🤖 17位投资大师

| # | 投资人 | Skill | 风格 | 核心指标 | 推荐模型 |
|---|--------|-------|------|---------|---------|
| 1 | 🏆 **Warren Buffett** | `augur-buffett` | 护城河价值投资 | 毛利率>40%、ROE>15%、负债<50% | claude-sonnet-4-6 |
| 2 | 📊 **Benjamin Graham** | `augur-graham` | 深度价值/安全边际 | PE<15、PB<1.5、流动比>2 | claude-sonnet-4-6 |
| 3 | 🚀 **Peter Lynch** | `augur-lynch` | GARP成长 | PEG<1.5、营收增速>15% | claude-sonnet-4-6 |
| 4 | 🌐 **Ray Dalio** | `augur-dalio` | 宏观/全天候 | 四象限分析、债务周期 | claude-sonnet-4-6 |
| 5 | 🧠 **Charlie Munger** | `augur-munger` | 格栅理论/多元思维 | ROE>20%、护城河+管理层 | claude-sonnet-4-6 |
| 6 | 🔄 **George Soros** | `augur-soros` | 反身性/宏观交易 | 反身性信号、趋势动量 | claude-sonnet-4-6 |
| 7 | 📉 **Howard Marks** | `augur-marks` | 周期/逆向投资 | 周期位置、市场情绪 | claude-sonnet-4-6 |
| 8 | 💡 **Cathie Wood** | `augur-cathie-wood` | 颠覆性创新 | 营收增速>30%、TAM | claude-sonnet-4-6 |
| 9 | 🔬 **Philip Fisher** | `augur-fisher` | 成长股/闲聊法 | 研发>10%、毛利率>50% | claude-sonnet-4-6 |
| 10 | 🥇 **ARPS** | `augur-arps` | Crypto/黄金宏观 | BTC相关性、黄金避险 | claude-sonnet-4-6 |
| 11 | 🤖 **Leopold Aschenbrenner** | `augur-aschenbrenner` | AI地缘政治 | AI投入、算力需求 | claude-opus-4-7 |
| 12 | ₿🇨🇳 **大宇 (BTCdayu)** | `augur-dayu` | 信息差/情绪动量 | 情绪动量>估值 | deepseek-v4 |
| 13 | 🏢 **Peter Thiel** | `augur-thiel` | 从0到1垄断 | 网络效应、技术壁垒 | claude-sonnet-4-6 |
| 14 | 🎯 **段永平** 🇨🇳 | `augur-duan-yongping` | 本分·极度集中 | 商业模式清晰、管理层本分 | deepseek-v4 |
| 15 | 🌏 **张磊 (高瓴)** 🇨🇳 | `augur-zhang-lei` | 长期结构性价值 | 营收增速>15%、结构性赛道 | deepseek-v4 |
| 16 | 🏔️ **李录 (喜马拉雅)** 🇨🇳 | `augur-li-lu` | 深度价值·安全边际 | PE<25、ROE>12%、无高负债 | claude-sonnet-4-6 |
| 17 | 🫖 **但斌 (东方港湾)** 🇨🇳 | `augur-dan-bin` | 品牌护城河·时代β | 毛利率>40%、定价权 | kimi-k2 |

> 📖 每位投资人都有：完整人格文档（`personas/*.md`）· 独立 Skill（`skills/*/SKILL.md`）· Python分析引擎（`scanner/personas/*.py`）

---

## 🧬 人格进化追踪

投资人的判断不是静态的。系统追踪每位大师的持仓变化、风格漂移与关键事件，分析时自动注入当前状态上下文。

| 投资人 | 关键进化时间线 | 核心漂移 |
|--------|-------------|---------|
| **Warren Buffett** | 1965 伯克希尔 → 1988 可口可乐 → 1998 Gen Re (失误) → 2011 逆向买BAC → 2016 苹果 (接受科技) → 2026 CRCL (接受加密) | 纯烟蒂 → 护城河成长 → 接受科技 |
| **Charlie Munger** | 1972 See's Candies教会他护城河 → 2002 中国价值机会 → 2004 Daily Journal → 2020 比亚迪 → 2023 临终前仍坚守原则 | 格雷厄姆式 → 多元思维格栅 → 中国价值 |
| **Ray Dalio** | 1975 桥水创立 → 1982 墨西哥危机押注失误 → 2008 唯一看对次贷危机的大基金 → 2012 全天候策略 → 2022 中国减仓 | 纯宏观 → 系统化机制 → 全天候 |
| **段永平** | 1989 小霸王 → 2001 步步高美国 → 2011 苹果大举建仓 → 2022 腾讯/网易港股 → 2023 持续持有茅台 | 企业家投资 → 价值集中 → 跨市场 |
| **张磊 (高瓴)** | 2005 $2000万 → 腾讯/百度早期 → 2012 京东 → 2019 格力混改 → 2021 减仓互联网 → 2022 新能源转型 | 中国互联网 → 消费医疗 → 新能源 |
| **李录 (喜马拉雅)** | 1989 流亡→耶鲁 → 1998 创立基金 → 2002 比亚迪 (20年持有) → 2015 加仓韩国POSCO → 2023 重仓Alphabet | 深度价值 → 亚洲价值机会 → 全球集中 |
| **但斌 (东方港湾)** | 1999 东方港湾创立 → 2003 茅台 → 2015-16 市场崩盘坚守 → 2020 坚持腾讯 → 2023 布局AI消费 | 消费品牌 → 永不卖茅台 → AI+消费 |
| **大宇 (BTCdayu)** | 2021 BTC 3000布局 → 2022 熊市减仓 → 2023 新叙事轮换 → 2024 MEME爆发 → 2026 AI+Crypto融合 | 技术分析 → 信息差驱动 → 叙事动量 |

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/BruceLanLan/augur.git
cd augur
pip install -e .
# 或从 PyPI (coming soon)
# pip install augur-agents
```

---

## 🖥️ CLI 命令行

```bash
# 列出所有投资人
augur list-personas

# 单投资人分析
augur analyze AAPL --persona buffett --pe 32 --roe 0.55 --gross-margins 0.46

# 17位大师共识
augur consensus AAPL --pe 32 --roe 0.55 --gross-margins 0.46

# 启动 MCP Server (供 Hermes/Claude 等调用)
augur mcp-server

# 启动 REST API
augur api --port 8900

# 注入投资人灵魂到 Profile
augur inject-soul --profile my-buffett --persona buffett --format hermes

# Telegram Bot
augur telegram

# Slack Bot
augur slack                    # Socket Mode (开发)
augur slack --mode http --port 3000  # HTTP Mode (生产)

# WeChat/微信 Bot
augur wechat                   # 企业微信模式 (接收+发送)
augur wechat --mode webhook    # Webhook 推送模式

# Lark/飞书 Bot
augur lark                     # Event 订阅模式
augur lark --mode webhook      # Webhook 推送模式

# Cron 定时分析
augur cron-run             # 手动运行一次
augur cron-start           # 启动定时守护进程

# Watchlist 管理
augur watchlist-add AAPL --pe 32 --roe 0.55
augur watchlist-show
```

---

## 📱 Telegram Bot

Augur 支持通过 Telegram Bot 进行实时分析，随时随地获取17位大师的投资建议。

### 创建 Bot

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/newbot`，按提示创建 Bot
3. 获得 Bot Token（格式如 `123456789:ABCdefGHI...`）

### 配置与启动

```bash
# 安装 telegram 依赖
pip install 'augur-agents[telegram]'

# 设置 Token
export TELEGRAM_TOKEN='your-bot-token-here'

# 启动 Bot
augur telegram
```

### Bot 可用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/analyze TICKER [指标]` | 17位大师共识分析 | `/analyze AAPL pe=32 roe=0.55` |
| `/consensus TICKER` | 共识分析(同 /analyze) | `/consensus NVDA` |
| `/ask PERSONA 问题` | 向特定大师提问 | `/ask buffett 分析AAPL` |
| `/personas` | 列出所有投资大师 | `/personas` |
| `/help` | 显示帮助 | `/help` |

### 自然语言对话

直接发送包含 `@人名` 的消息即可触发对应大师分析：

```
@巴菲特 分析AAPL
@段永平 NVDA值得买吗？
@张磊 PDD是时代级赛道吗？
```

---

## 💬 Slack Bot

Augur 支持通过 Slack Bot 进行实时分析，支持 Socket Mode（开发）和 HTTP Mode（生产）两种模式。

### 创建 Slack App

1. 前往 [api.slack.com/apps](https://api.slack.com/apps)，点击 "Create New App"
2. 选择 "From scratch"，输入名称（如 "Augur"）并选择 Workspace
3. 在 "OAuth & Permissions" 中添加 Bot Token Scopes:
   - `chat:write` - 发送消息
   - `app_mentions:read` - 读取 @augur 提及
   - `commands` - 支持 Slash Commands
   - `im:read` / `im:write` - 私聊消息
4. Install to Workspace，获取 Bot User OAuth Token (`xoxb-...`)
5. (Socket Mode) 在 "Basic Information" > "App-Level Tokens" 生成 Token (`xapp-...`)，Scope: `connections:write`

### 配置与启动

```bash
# 安装 slack 依赖
pip install 'augur-agents[slack]'

# Socket Mode (推荐开发用)
export SLACK_BOT_TOKEN='xoxb-your-bot-token'
export SLACK_APP_TOKEN='xapp-your-app-token'
augur slack

# HTTP Mode (生产环境，需配置 Request URL)
export SLACK_BOT_TOKEN='xoxb-your-bot-token'
export SLACK_SIGNING_SECRET='your-signing-secret'
augur slack --mode http --port 3000
```

### Slash Commands

| 命令 | 说明 | 示例 |
|------|------|------|
| `/augur-analyze TICKER [指标]` | 17位大师共识分析 | `/augur-analyze AAPL pe=32 roe=0.55` |
| `/augur TICKER [指标]` | 快捷共识分析 | `/augur NVDA pe=45` |
| `/augur-ask PERSONA 问题` | 向特定大师提问 | `/augur-ask buffett analyze AAPL` |
| `/augur-personas` | 列出所有投资大师 | `/augur-personas` |
| `/augur-help` | 显示帮助 | `/augur-help` |

### App Mention & DM

在频道中 @augur 即可触发分析：

```
@augur analyze AAPL pe=32 roe=0.55
@augur @buffett analyze AAPL
```

直接私聊 Bot 发送包含股票代码的消息也可触发分析。

### Block Kit 格式输出

Slack Bot 使用 Block Kit 进行富文本输出，包含：
- Header: 分析标题
- Section fields: 信号/评分/置信度
- Agent 明细列表
- 关键发现与风险提示
- Context footer

---

## 📱 微信 Bot (WeChat/WeCom)

Augur 支持通过企业微信进行实时分析，支持企业微信应用模式和 Webhook 推送模式。

### 创建企业微信应用

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/)
2. 应用管理 > 自建 > 创建应用
3. 记录 Corp ID, Agent ID, Secret
4. 设置接收消息的回调 URL
5. 获取 Token 和 EncodingAESKey

### 配置与启动

```bash
# 安装微信依赖
pip install 'augur-agents[wechat]'

# 企业微信模式 (接收+发送)
export WECHAT_CORP_ID='your_corp_id'
export WECHAT_CORP_SECRET='your_corp_secret'
export WECHAT_AGENT_ID='your_agent_id'
export WECHAT_TOKEN='your_token'
export WECHAT_AES_KEY='your_aes_key'
augur wechat --mode wecom --port 8080

# Webhook 模式 (仅推送, 配合 Cron)
export WECHAT_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx'
augur wechat --mode webhook
```

### 可用命令 (群聊/私聊)

| 命令 | 说明 | 示例 |
|------|------|------|
| `分析 TICKER [指标]` | 17位大师共识分析 | `分析 AAPL pe=32 roe=0.55` |
| `@巴菲特 TICKER` | 向特定大师提问 | `@段永平 NVDA` |
| `问 PERSONA TICKER` | 同上(英文ID) | `问 buffett AAPL` |
| `投资人列表` | 列出所有投资大师 | `投资人列表` |
| `帮助` | 显示帮助 | `帮助` |

### Webhook 群机器人配置

群机器人 Webhook 适合配合 Cron 定时推送:

```yaml
# ~/.augur/watchlist.yaml
notifications:
  wechat:
    enabled: true
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
```

---

## 🐦 飞书 Bot (Lark/Feishu)

Augur 支持通过飞书进行实时分析，支持事件订阅模式和 Webhook 推送模式。

### 创建飞书应用

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 开启机器人能力
5. 配置事件订阅 URL，订阅 `im.message.receive_v1`
6. 获取 Verification Token 和 Encrypt Key

### 配置与启动

```bash
# 安装飞书依赖
pip install 'augur-agents[lark]'

# Event 订阅模式 (接收+发送)
export LARK_APP_ID='your_app_id'
export LARK_APP_SECRET='your_app_secret'
export LARK_VERIFICATION_TOKEN='your_token'
export LARK_ENCRYPT_KEY='your_key'
augur lark --mode event --port 9000

# Webhook 模式 (仅推送)
export LARK_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'
augur lark --mode webhook
```

### 可用命令 (群聊/私聊)

| 命令 | 说明 | 示例 |
|------|------|------|
| `分析 TICKER [指标]` | 17位大师共识分析 | `分析 AAPL pe=32 roe=0.55` |
| `@巴菲特 TICKER` | 向特定大师提问 | `@张磊 PDD` |
| `问 PERSONA TICKER` | 同上(英文ID) | `问 li_lu GOOGL` |
| `投资人列表` | 列出所有投资大师 | `投资人列表` |
| `帮助` | 显示帮助 | `帮助` |

### 飞书卡片消息

飞书 Bot 使用交互式卡片 (Interactive Card) 进行富文本输出:
- Header: 信号颜色(绿/红/黄) + 标题
- Fields: 信号/评分/置信度
- Agent 明细列表
- 关键发现与风险

### Webhook 群机器人配置

```yaml
# ~/.augur/watchlist.yaml
notifications:
  lark:
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

---

## ⏰ Cron 定时分析 + Watchlist

### Watchlist 管理

```bash
# 添加自选股
augur watchlist-add AAPL --pe 32 --roe 0.55 --gross-margins 0.46
augur watchlist-add NVDA --pe 45 --roe 0.85
augur watchlist-add TSLA --pe 85 --roe 0.12

# 查看自选股
augur watchlist-show

# 手动触发一次分析
augur cron-run

# 启动定时守护进程
augur cron-start
```

### 配置文件 (~/.augur/watchlist.yaml)

```yaml
watchlist:
  - ticker: AAPL
    pe: 32
    roe: 0.55
    gross_margins: 0.46
  - ticker: NVDA
    pe: 45
    roe: 0.85
    gross_margins: 0.75
  - ticker: TSLA
    pe: 85
    roe: 0.12
    gross_margins: 0.18

schedule:
  cron: "0 9 * * 1-5"   # 工作日 9:00 AM
  timezone: "Asia/Shanghai"

notifications:
  telegram:
    enabled: true
    chat_id: "YOUR_CHAT_ID"
    token: "YOUR_BOT_TOKEN"
  slack:
    enabled: true
    channel: "#investment-signals"
    token: "xoxb-YOUR-BOT-TOKEN"
  wechat:
    enabled: true
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  lark:
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  alert_threshold: 3      # 评分变化>3才推送
```

### Cron 定时触发

使用 `augur cron-start` 启动守护进程，按配置的 cron 表达式自动执行分析并推送到 Telegram、Slack、微信和飞书。

---

## 🐳 Docker 部署

### 快速启动 (Dashboard + API)
```bash
docker compose up -d dashboard
# → http://localhost:8000
```

### 启动 Telegram Bot
```bash
export TELEGRAM_TOKEN=your_token
docker compose --profile telegram up -d
```

### 启动全部服务
```bash
docker compose --profile full --profile telegram --profile cron up -d
```

### 自定义配置
```bash
# 编辑 config/agents.yaml 修改模型配置
# 编辑 .env 填入 Bot Token
docker compose up -d --build
```

### Makefile 快捷命令
```bash
make docker-build    # 构建镜像
make docker-up       # 启动 Dashboard
make docker-down     # 停止所有服务
make docker-full     # 启动全部服务 (含 Telegram + Cron)
```

---

## 🔗 MCP Server 集成

Augur 提供标准 MCP (Model Context Protocol) Server，可供 Hermes、Claude Desktop 等 Agent 系统直接调用。

### 可用工具 (6 Tools)

| 工具 | 说明 |
|------|------|
| `augur_analyze` | 单投资人分析指定标的 |
| `augur_consensus` | 17位大师共识分析 |
| `augur_list_personas` | 列出所有可用投资人 |
| `augur_configure` | 运行时配置管理 |
| `augur_create_persona` | 创建自定义投资人人格 |
| `augur_debate` | 多Agent辩论模式 |

### Hermes 配置 (~/.hermes/config.yaml)

```yaml
mcp_servers:
  augur-agents:
    command: augur
    args: [mcp-server]
    description: "17位投资大师分析系统"
```

### Claude Desktop 配置 (claude_desktop_config.json)

```json
{
  "mcpServers": {
    "augur-agents": {
      "command": "augur",
      "args": ["mcp-server"],
      "description": "Multi-agent investment analysis with 17 investor personas"
    }
  }
}
```

配置完成后，在 Hermes/Claude 对话中即可直接调用：
```
请用巴菲特框架分析 AAPL，PE=32，毛利率46%，ROE=55%
```

Agent 会自动调用 `augur_analyze` 工具完成分析。

---

### Web Dashboard

```bash
python3 -m dashboard.app
# → 打开浏览器访问 http://localhost:8000
# → 在股票分析页输入 AAPL、NVDA 等开始分析
```

### 命令行分析（17位大师共识）

```bash
python3 -c "
from scanner.personas.registry import AgentRegistry, DecisionCoordinator
from scanner.personas.base import MarketContext

reg = AgentRegistry()
coord = DecisionCoordinator(reg)
ctx = MarketContext(ticker='AAPL', price=210, pe=32, gross_margins=0.46,
                    roe=0.55, revenue_growth=0.08, sector='Technology')

results = coord.analyze_with_all(ctx)
consensus = coord.get_consensus(results, ticker='AAPL', context=ctx)

for agent_id, r in results.items():
    print(f'{r.agent_name:>30}: {r.signal.value.upper():>8} ({r.score:.1f}/10)')

print(f'\n共识信号: {consensus.signal.value.upper()} | 综合评分: {consensus.score:.1f}/10')
"
```

### 实时 SEC 13F 持仓数据

```bash
# 获取最新实盘持仓（直接从SEC EDGAR拉取）
python3 scripts/sec_holdings.py buffett zhang_lei li_lu duan_yongping --no-save
```

### 自定义人格（YAML）

在 `personas/custom/` 下创建 YAML 文件即可自动注册：

```yaml
agent_id: my_quant
name: "我的量化策略"
scoring_weights:
  momentum: 0.50
  value: 0.50
factors:
  momentum:
    base: 5
    rules:
      - {if: "rsi > 60 and rsi < 75", add: 2}
      - {if: "macd > macd_signal", add: 1}
```

---

## 📊 Web Dashboard

Bloomberg 风格的暗色主题 Web 界面，内置 FastAPI 服务：

```
🏠 首页     — 系统概览 + 快速分析(输入代码即得共识) + 系统状态
🤖 人格页   — 17位大师卡片网格 + 头像 + 搜索筛选 + 展开详情
📈 股票分析  — 单标的深度分析 + 实时17Agent评分 + 可展开推理
⚡ 信号监控  — 自选股批量扫描（开发中）
⚙️ 设置     — Agent模型配置(17投资人独立模型选择 + 实时保存)
```

启动方式：
```bash
python3 -m dashboard.app --port 8000 --cors
```

### REST API Endpoints

Dashboard 内置 REST API，支持前端配置管理和外部集成：

| Endpoint | Method | 说明 |
|----------|--------|------|
| `/api/config` | GET | 获取完整配置（agents.yaml 内容） |
| `/api/config` | PUT | 更新完整配置 |
| `/api/config/persona/{id}` | GET | 获取单个投资人的模型配置 |
| `/api/config/persona/{id}` | PUT | 更新单个投资人的模型 |
| `/api/models` | GET | 列出所有可用模型 |
| `/api/custom-persona` | POST | 创建自定义投资人（YAML） |
| `/api/schema/persona` | GET | 获取 Persona YAML Schema |
| `/api/personas` | GET | 获取所有投资人列表 |
| `/api/analyze/{ticker}` | GET | 17位大师共识分析 |
| `/api/persona/{agent_id}` | GET | 获取单个投资人详情 |
| `/health` | GET | 健康检查 |

---

## 🔌 整合到任意平台

> 📖 **详细指南 → [docs/agent-integration-guide.md](docs/agent-integration-guide.md)**
>
> 包含 17位Agent × 7种平台形态的完整接入步骤、配置示例、架构概览与自定义接入说明。

<p align="center">
  <img src="docs/images/skills-deploy.svg" alt="Skills Deploy" width="100%"/>
</p>

每位投资人都是一个独立的 Skill，遵循 [agentskills.io](https://agentskills.io) 标准，可部署到任意平台：

### Hermes Web UI / Claude / OpenClaw

```bash
# 安装完整 Augur 系统（17位大师）
hermes skills install https://github.com/BruceLanLan/augur

# 或安装单个投资人 Skill
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/buffett
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/zhang_lei
```

安装后在对话中直接调用：
```
/skill augur-buffett
"帮我用巴菲特框架分析 AAPL，PE=32，毛利率46%，ROE=55%"

/skill augur-zhang-lei
"张磊视角评估 PDD，营收增速86%，这是时代级赛道吗？"
```

### Telegram / Slack / 微信 / 飞书

```bash
# 启动 Augur API
python3 -m dashboard.app --port 8000 --cors

# === Telegram Bot (已完成) ===
export TELEGRAM_TOKEN=your_bot_token
augur telegram
# 用户在 Telegram 发送：
# /analyze AAPL pe=32 gm=46 roe=55
# /ask buffett 你觉得现在的苹果值得持有吗？

# === Slack Bot (已完成) ===
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_APP_TOKEN=xapp-your-app-token
augur slack
# 用户在 Slack 发送：
# /augur-analyze AAPL pe=32 roe=0.55
# /augur-ask buffett analyze AAPL
# 或 @augur analyze AAPL

# === WeChat/微信 Bot (已完成 v4.6) ===
export WECHAT_CORP_ID=your_corp_id
export WECHAT_CORP_SECRET=your_corp_secret
export WECHAT_AGENT_ID=your_agent_id
export WECHAT_TOKEN=your_token
export WECHAT_AES_KEY=your_aes_key
augur wechat                   # 企业微信模式
augur wechat --mode webhook    # Webhook 推送模式

# === Lark/飞书 Bot (已完成 v4.6) ===
export LARK_APP_ID=your_app_id
export LARK_APP_SECRET=your_app_secret
export LARK_VERIFICATION_TOKEN=your_token
augur lark                     # Event 订阅模式
augur lark --mode webhook      # Webhook 推送模式
```

### 配置每位 Agent 的模型

编辑 `config/agents.yaml`，为不同投资人指定最适合的 LLM：

```yaml
per_agent:
  buffett:       claude-sonnet-4-6   # 英文价值分析
  duan_yongping: deepseek-v4         # 中文理解更准确
  dan_bin:       kimi-k2             # 中国消费文化语境
  aschenbrenner: claude-opus-4-7     # AI地缘政治需最强推理
  dayu:          deepseek-v4         # 币圈叙事，中文社区
```

支持所有主流模型：`claude-*` · `gpt-4o*` · `deepseek-v4` · `kimi-k2` · `minimax-01` · 本地 Ollama

---

## 🧠 共识机制

<p align="center">
  <img src="docs/images/consensus-flow.svg" alt="Consensus Flow" width="100%"/>
</p>

17位Agent各自独立分析，通过6层加权机制汇总为最终共识信号：

1. **行业感知权重** — 科技股给 Aschenbrenner/Wood 更高权重，消费股给 Buffett/Munger 更高权重
2. **市场机制路由** — 熊市时 Marks/Dalio 权重提升，牛市时 Lynch/Fisher 权重提升
3. **滚动 IC 权重** — 历史预测准确率高的 Agent 动态加权
4. **多样性相关性惩罚** — 观点高度相似的 Agent 减少冗余权重
5. **Kelly 仓位建议** — 基于共识信号和置信度给出建议仓位比例
6. **风险管理否决层** — 高负债 + 熊市信号时可否决共识看多

---

## 🏗️ 项目架构

<p align="center">
  <img src="docs/images/architecture-baoyu.svg" alt="Augur Architecture" width="100%"/>
</p>

```
augur/
│
├── src/augur/                  # pip 包主模块 (augur-agents)
│   ├── __init__.py             # 公共符号导出
│   ├── cli.py                  # Click CLI: 11 commands
│   ├── mcp_server.py           # MCP Server: 6 tools (stdio mode)
│   ├── api.py                  # REST API (FastAPI)
│   ├── config.py               # 运行时配置管理
│   ├── registry.py             # AgentRegistry + DecisionCoordinator
│   ├── coordinator.py          # 共识协调器
│   ├── persona_loader.py       # YAML 自定义人格加载
│   ├── soul.py                 # Soul Injector - 人格注入引擎
│   ├── cron.py                 # Cron 定时分析 + Watchlist 管理
│   ├── bots/                   # 多平台 Bot 适配器
│   │   ├── __init__.py
│   │   ├── telegram_bot.py     # Telegram Bot (python-telegram-bot)
│   │   ├── slack_bot.py        # Slack Bot (slack-bolt, Socket + HTTP)
│   │   ├── wechat_bot.py       # WeChat/微信 Bot (wechatpy, 企业微信 + Webhook)
│   │   └── lark_bot.py         # Lark/飞书 Bot (Event + Webhook)
│   └── personas/               # 17位投资人人格 Agent
│       ├── base.py             # Agent基类、MarketContext、AgentResponse
│       ├── buffett.py          # Warren Buffett (沃伦·巴菲特)
│       ├── graham.py           # Benjamin Graham (本杰明·格雷厄姆)
│       ├── lynch.py            # Peter Lynch (彼得·林奇)
│       ├── dalio.py            # Ray Dalio (瑞·达利欧)
│       ├── munger.py           # Charlie Munger (查理·芒格)
│       ├── soros.py            # George Soros (乔治·索罗斯)
│       ├── marks.py            # Howard Marks (霍华德·马克斯)
│       ├── cathie_wood.py      # Cathie Wood (凯西·伍德)
│       ├── fisher.py           # Philip Fisher (菲利普·费雪)
│       ├── arps.py             # ARPS (Crypto/黄金宏观)
│       ├── aschenbrenner.py    # Leopold Aschenbrenner
│       ├── dayu.py             # 大宇 (BTCdayu)
│       ├── thiel.py            # Peter Thiel (彼得·蒂尔)
│       ├── duan_yongping.py    # 段永平 (Duan Yongping) 🇨🇳
│       ├── zhang_lei.py        # 张磊 (Zhang Lei/高瓴) 🇨🇳
│       ├── li_lu.py            # 李录 (Li Lu/喜马拉雅) 🇨🇳
│       └── dan_bin.py          # 但斌 (Dan Bin/东方港湾) 🇨🇳
│
├── scanner/                    # 向后兼容 shim (导入重定向到 src/augur/)
│   ├── personas/               # → augur.personas.*
│   └── persona_loader.py       # → augur.persona_loader
│
├── skills/                     # 独立 Skill 封装（agentskills.io 标准）
│   ├── buffett/SKILL.md        # augur-buffett Skill
│   ├── graham/SKILL.md         # augur-graham Skill
│   ├── zhang_lei/SKILL.md      # augur-zhang-lei Skill
│   ├── li_lu/SKILL.md          # augur-li-lu Skill
│   ├── duan_yongping/SKILL.md  # augur-duan-yongping Skill
│   ├── dan_bin/SKILL.md        # augur-dan-bin Skill
│   └── ... (17个，每个可独立部署)
│
├── config/
│   └── agents.yaml             # 每个 Agent 的 LLM 模型配置
│
├── personas/                   # 投资人深度文档
│   ├── buffett.md              # 人格 + 持仓 + 进化时间线
│   ├── dan-bin.md
│   ├── duan-yongping.md
│   ├── zhang-lei.md
│   ├── li-lu.md
│   ├── ... (17份)
│   └── custom/                 # YAML自定义人格
│
├── dashboard/                  # Bloomberg风格 Web UI
│   ├── app.py                  # FastAPI + 所有路由
│   └── templates/              # 首页/股票分析/人格/占位页
│
├── pyproject.toml              # pip 包配置 (augur-agents)
├── SKILL.md                    # 主 Skill（17位大师统一调度）
└── README.md                   # 本文件
```

---

## 📋 版本日志

| 版本 | 日期 | 内容 |
|------|------|------|
| **v5.0** | 2026-05-23 | 🐳 Docker 容器化 — Dockerfile + docker-compose 多服务编排 |
| **v4.6** | 2026-05-23 | 📱 微信 (企业微信+Webhook) + 飞书 (Event+Webhook) Bot 多平台适配 |
| **v4.5** | 2026-05-23 | 📊 信号监控页 + 自定义投资人 UI 创建器 + Watchlist API + requirements.txt |
| **v4.4** | 2026-05-22 | 🎨 Dashboard UI 全面升级 - Bloomberg Terminal 风格 + Hermes 侧边栏布局 |
| **v4.3** | 2026-05-22 | 💬 Slack Bot (Socket Mode + HTTP) + Cron Slack 推送 |
| **v4.2** | 2026-05-22 | 📱 Telegram Bot + Cron 定时共识分析 + Watchlist 管理 |
| **v4.1** | 2026-05-22 | 🎨 Config REST API + Dashboard UI/UX - 设置页完全可用(17投资人模型配置) + 人格页搜索/展开/头像 + 首页快速分析 + 股票页交互优化 + 响应式CSS |
| **v4.0** | 2026-05-22 | 🚀 pip 包化 — `augur-agents` PyPI 包 + CLI 6命令 + MCP Server 6工具 + 运行时配置管理 |
| **v3.5** | 2026-05-22 | 🎨 Baoyu漫画风格配图 — hero-banner-baoyu + architecture-baoyu + 17投资人漫画头像 |
| **v3.4** | 2026-05-21 | 🔌 Skill封装 — 17个独立Agent Skill + 模型配置 + README全面升级 |
| **v3.3** | 2026-05-21 | 📊 FastAPI dashboard 完整实现（首页/股票分析/人格/占位页） |
| **v3.2** | 2026-05-21 | 🇨🇳 4位中国投资人加入（段永平/张磊/李录/但斌）— 17位大师 |
| **v3.1** | 2026-05-21 | 📋 SEC EDGAR 13F 数据获取器（正确CIK + 动态文件名解析） |
| **v3.0** | 2026-05-21 | 🦉 正式更名为 Augur + DecisionCoordinator 共识引擎 |
| **v2.0.4** | 2026-05-21 | 🏢 Peter Thiel (彼得·蒂尔) 垄断框架加入 |
| **v2.0** | 2026-05-21 | 🎉 13位完整投资人人格系统 + 完整扫描器基础设施 |
| **v1.6** | 2026-05-21 | 📈 投资人进化追踪系统 (PersonaEvolutionTracker) |
| **v1.5** | 2026-05-21 | ₿ 大宇 (BTCdayu) 币圈投资人格 + YAML自动加载 |
| **v1.0** | 2026-05 | 🌱 初始版本：巴菲特单人格分析 |

---

## 🗺️ 路线图

- [x] **v1.0-v2.0**: 1位 → 13位投资人人格
- [x] **v3.0**: 正式更名 Augur + 多Agent共识引擎
- [x] **v3.1**: SEC EDGAR 13F 实时持仓获取
- [x] **v3.2**: 4位中国投资人（段永平/张磊/李录/但斌）
- [x] **v3.3**: Bloomberg风格 Web Dashboard（全5页路由）
- [x] **v3.4**: 17个独立 Skill 封装 + LLM 模型配置
- [x] **v4.0**: pip 包化 `augur-agents` + CLI 6命令 + MCP Server + Soul Injector
- [x] **v4.1**: Config REST API + Dashboard UI/UX 全面优化
- [x] **v4.2**: Telegram Bot + Cron 定时共识分析 + Watchlist 管理
- [x] **v4.3**: Slack Bot (Socket Mode + HTTP Mode) + Cron Slack 推送
- [x] **v4.4**: Bloomberg Terminal UI + Hermes 侧边栏布局 (纯CSS, 无Bootstrap)
- [x] **v4.5**: 信号监控页 + 自定义投资人 UI 创建器 + Watchlist API + requirements.txt
- [x] **v4.6**: WeChat/微信 + Lark/飞书 Bot 多平台适配
- [x] **v5.0**: Docker 容器化 + docker-compose 多服务编排 + Makefile
- [ ] **v5.1**: 历史回测系统 + Agent IC 实盘追踪

---

## 🏛️ 为什么叫 Augur？

> **Augur（奥格）** — 拉丁语，古罗马的占卜官。在古罗马，Augur 专门负责**解读征兆、预测未来**——从鸟群的轨迹、闪电的方向中，看见即将到来的变化。这正是这个系统要做的事：让17位投资大师帮你在市场变化之前看见先机。

### 与 Hermes 的呼应

| 神祇 | 角色 | 象征 |
|------|------|------|
| **Hermes** (赫尔墨斯) | 神的信使，传递信息 | 信息传递、沟通 |
| **Augur** (奥格) | 解读征兆，预测未来 | 分析解读、先见之明 |

Hermes Agent 负责**传递信息**，Augur 负责**解读信息**。一个传信，一个预测，天然互补。

---

## 🤝 贡献指南

欢迎通过各种方式贡献：

1. **新投资人人格** — 在 `personas/custom/` 下添加 YAML 文件即可，或参考 `scanner/personas/buffett.py` 写 Python Agent
2. **新 Skill** — 参考 `skills/buffett/SKILL.md` 格式，为任意投资风格创建独立 Skill
3. **算法优化** — 改进 `scanner/personas/` 中的评分逻辑或 `registry.py` 中的共识机制
4. **Bot 适配** — 在 `bots/` 目录下添加 Telegram/Slack/WeChat 适配器
5. **Web UI增强** — 完善 `dashboard/` 前端界面

---

## Star History

<a href="https://www.star-history.com/?repos=BruceLanLan%2Faugur&type=timeline&logscale=&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=BruceLanLan/augur&type=timeline&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=BruceLanLan/augur&type=timeline&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=BruceLanLan/augur&type=timeline&legend=top-left" />
 </picture>
</a>

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/BruceLanLan">BruceLanLan</a></sub>
  <br>
  <sub>Special thanks to <a href="https://dayu.xyz">大宇 (BTCdayu)</a> for Crypto investment philosophy</sub>
</p>
